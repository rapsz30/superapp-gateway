// S7a (hanya dijalankan bila -IncludeLlm diaktifkan):
// Judul get-recommendations dengan 1, 2, 3 VU, masing-masing 6 permintaan dengan jeda minimal 12 detik per VU.
// Berhenti seketika bila muncul "no credits", HTTP 429, atau 3 galat beruntun.

import http from 'k6/http';
import { sleep } from 'k6';
import exec from 'k6/execution';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  getValidToken,
  recordMainMetrics,
  registerAndLogin,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const VUS = Math.min(Number(__ENV.VUS || 1), 3);

let consecutiveErrors = 0;

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: {
    main: {
      executor: 'per-vu-iterations',
      vus: VUS,
      iterations: 6,
      maxDuration: '5m',
      tags: { phase: 'main' },
    },
  },
  thresholds: buildThresholds(),
};

export function setup() {
  return registerAndLogin(BASE);
}

export default function (data) {
  const token = getValidToken(data);
  const payload = JSON.stringify({
    interests:
      'sistem deteksi kantuk untuk pengemudi menggunakan computer vision dan machine learning',
  });

  const res = http.post(`${BASE}/api/judul-recommender/get-recommendations`, payload, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    timeout: '60s',
  });

  recordMainMetrics(res, 200);

  const bodyText = (res.body || '').toLowerCase();
  if (res.status === 429 || bodyText.indexOf('no credits') !== -1) {
    exec.test.abort(`S7 dihentikan karena kuota/rate limit LLM (HTTP ${res.status})`);
  }

  if (res.status !== 200) {
    consecutiveErrors += 1;
    if (consecutiveErrors >= 3) {
      exec.test.abort('S7 dihentikan karena 3 galat beruntun pada Judul LLM');
    }
  } else {
    consecutiveErrors = 0;
  }

  sleep(12);
}

