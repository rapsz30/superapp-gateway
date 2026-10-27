// S7b (hanya dijalankan bila -IncludeLlm diaktifkan):
// Micro-cred: 1, 2, 3 siklus assessment serentak (start, submit, poll sampai completed maks 120 detik).
// Body disusun mengikuti skema /openapi.json. Berhenti bila muncul "no credits", 429, atau 3 galat beruntun.

import http from 'k6/http';
import { sleep } from 'k6';
import exec from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  recordMainMetrics,
  registerAndLogin,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const DIRECT_MICROCRED = __ENV.DIRECT_MICROCRED || 'http://microcred-api:8000';
const VUS = Math.min(Number(__ENV.VUS || 1), 3);

const cycleDurationMs = new Trend('cycle_duration_ms', true);
const cycleSuccess = new Counter('cycle_completed');
let consecutiveErrors = 0;

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: {
    main: {
      executor: 'per-vu-iterations',
      vus: VUS,
      iterations: 1,
      maxDuration: '3m',
      tags: { phase: 'main' },
    },
  },
  thresholds: buildThresholds(),
};

function buildEssayText(prompt) {
  const p = (prompt || '').toLowerCase();
  if (p.indexOf('put vs patch') !== -1) {
    return 'PUT mengganti seluruh resource secara idempoten, sedangkan PATCH memodifikasi sebagian field yang dikirim saja sehingga lebih hemat bandwidth.';
  }
  if (p.indexOf('/login') !== -1) {
    return 'Validasi payload email dan password, periksa hash password dengan bcrypt secara konstan, lalu terbitkan JWT pendek dengan klaim sub dan exp.';
  }
  return 'Desain menggunakan arsitektur modular dengan validasi input ketat, caching di Redis, serta observabilitas log terstruktur dan penanganan galat yang aman.';
}

function buildQuestionResponse(q) {
  const ans = { question_id: q.id };
  if (q.question_type === 'essay') {
    ans.answer_text = buildEssayText(q.prompt);
  } else if (q.question_type === 'theoretical') {
    const firstOpt = q.options && q.options.length > 0 ? q.options[0].id : 'A';
    ans.selected_option = firstOpt;
    ans.selected_option_id = firstOpt;
  } else {
    const meta = q.metadata || {};
    const caps = meta.captures || [];
    const acc = meta.accepted_values || [];
    const opts = q.options || [];
    if (caps.indexOf('project_count') !== -1) {
      const chosen = acc.slice(0, 2);
      ans.project_count = 3;
      ans.selected_options = chosen;
      ans.project_contexts = chosen;
    } else if (opts.length === 0) {
      const chosen = acc.slice(0, 3);
      ans.selected_options = chosen;
      ans.answer_text = chosen.join(', ');
    } else {
      ans.selected_option = opts[0].id;
    }
  }
  return ans;
}

export function setup() {
  // Baca /openapi.json untuk memastikan skema endpoint assessment tersedia
  const schemaRes = http.get(`${DIRECT_MICROCRED}/openapi.json`, { timeout: '10s' });
  let defaultRoleSlug = 'backend-engineer';
  if (schemaRes.status === 200) {
    try {
      const spec = schemaRes.json();
      const startSchema =
        spec &&
        spec.components &&
        spec.components.schemas &&
        spec.components.schemas.AssessmentStartRequest;
      if (startSchema && startSchema.properties && startSchema.properties.role_slug && startSchema.properties.role_slug.default) {
        defaultRoleSlug = startSchema.properties.role_slug.default;
      }
    } catch (_) {
      // Gunakan default backend-engineer
    }
  }
  return { roleSlug: defaultRoleSlug };
}

export default function (data) {
  // Setiap VU memakai satu akun mahasiswa tersendiri agar assessment serentak tidak berbenturan
  const acct = registerAndLogin(BASE);
  const token = acct.token;
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const startRes = http.post(
    `${BASE}/api/micro-cred/assessments/start`,
    JSON.stringify({ role_slug: data.roleSlug || 'backend-engineer' }),
    { headers: headers, timeout: '30s' }
  );
  recordMainMetrics(startRes, 200);

  if (startRes.status === 429 || (startRes.body || '').toLowerCase().indexOf('no credits') !== -1) {
    exec.test.abort(`S7 dihentikan pada start (HTTP ${startRes.status})`);
  }
  if (startRes.status !== 200) {
    consecutiveErrors += 1;
    if (consecutiveErrors >= 3) {
      exec.test.abort('S7 dihentikan karena 3 galat beruntun');
    }
    return;
  }

  const startJson = startRes.json();
  const assessmentId = startJson.assessment_id;
  const responses = (startJson.questions || []).map(buildQuestionResponse);

  const t0 = Date.now();
  const subRes = http.post(
    `${BASE}/api/micro-cred/assessments/${assessmentId}/submit`,
    JSON.stringify({ responses: responses }),
    { headers: headers, timeout: '60s' }
  );
  recordMainMetrics(subRes, [200, 202]);

  const subBody = (subRes.body || '').toLowerCase();
  if (subRes.status === 429 || subBody.indexOf('no credits') !== -1) {
    exec.test.abort(`S7 dihentikan pada submit karena kuota/rate limit LLM (HTTP ${subRes.status})`);
  }
  if (subRes.status !== 200 && subRes.status !== 202) {
    consecutiveErrors += 1;
    if (consecutiveErrors >= 3) {
      exec.test.abort('S7 dihentikan karena 3 galat beruntun pada submit');
    }
    return;
  }

  let finalStatus = 'timeout';
  while ((Date.now() - t0) / 1000 < 120) {
    const stRes = http.get(`${BASE}/api/micro-cred/assessments/${assessmentId}/status`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: '15s',
    });
    if (stRes.status === 429 || (stRes.body || '').toLowerCase().indexOf('no credits') !== -1) {
      exec.test.abort('S7 dihentikan saat polling karena no credits / 429');
    }
    if (stRes.status === 200) {
      const sj = stRes.json();
      if (sj && (sj.status === 'completed' || sj.status === 'failed')) {
        finalStatus = sj.status;
        break;
      }
    }
    sleep(2);
  }

  cycleDurationMs.add(Date.now() - t0);
  if (finalStatus === 'completed') {
    cycleSuccess.add(1);
    consecutiveErrors = 0;
  } else {
    consecutiveErrors += 1;
    if (consecutiveErrors >= 3) {
      exec.test.abort(`S7 dihentikan karena 3 siklus gagal/timeout (${finalStatus})`);
    }
  }
}

