// Helper bersama untuk skrip k6 pengujian kinerja gateway SuperApp.
// Token tidak pernah dicetak ke log atau konsol.

import http from 'k6/http';
import exec from 'k6/execution';
import { Counter, Rate, Trend } from 'k6/metrics';

export const mainDuration = new Trend('main_duration', true);
export const mainFailed = new Rate('main_failed');
export const mainReqs = new Counter('main_reqs');
export const mainTimeouts = new Counter('main_timeouts');
export const mainStatus200 = new Counter('main_status_200');
export const mainStatus400 = new Counter('main_status_400');
export const mainStatus401 = new Counter('main_status_401');
export const mainStatus413 = new Counter('main_status_413');
export const mainStatus503 = new Counter('main_status_503');
export const mainStatus5xx = new Counter('main_status_5xx');
export const mainStatusOther = new Counter('main_status_other');

export const SUMMARY_TREND_STATS = ['avg', 'min', 'med', 'max', 'p(50)', 'p(90)', 'p(95)', 'p(99)'];

// Ambang batas standar: batalkan uji bila error rate > 20% selama >= 15 detik pada tahap utama.
export function buildThresholds() {
  return {
    'http_req_duration{phase:main}': ['max>=0'],
    'http_req_failed{phase:main}': ['rate<=1'],
    main_duration: ['max>=0'],
    main_failed: [
      { threshold: 'rate<=0.20', abortOnFail: true, delayAbortEval: '15s' },
    ],
  };
}

// Daftar dan login satu akun uji pada setup(). Jangan mencetak email atau token.
export function registerAndLogin(baseUrl) {
  const ts = Date.now();
  const rnd = Math.floor(10000000 + Math.random() * 89999999);
  const email = `uji-perf-${ts}-${rnd}@example.com`;
  const password = 'Uji12345!';
  const nim = String(rnd);

  const regPayload = JSON.stringify({
    email: email,
    password: password,
    full_name: 'Mahasiswa Uji Kinerja',
    nim: nim,
    faculty: 'Fakultas Teknologi Industri',
    study_program: 'Informatika',
  });

  const regRes = http.post(`${baseUrl}/api/micro-cred/auth/register`, regPayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { phase: 'setup' },
    timeout: '30s',
  });

  if (regRes.status !== 201 && regRes.status !== 409) {
    exec.test.abort(`Setup registrasi gagal dengan status HTTP ${regRes.status}`);
  }

  const loginPayload = JSON.stringify({ email: email, password: password });
  const loginRes = http.post(`${baseUrl}/api/micro-cred/auth/login`, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { phase: 'setup' },
    timeout: '30s',
  });

  if (loginRes.status !== 200) {
    exec.test.abort(`Setup login gagal dengan status HTTP ${loginRes.status}`);
  }

  let body = null;
  try {
    body = loginRes.json();
  } catch (_) {
    exec.test.abort('Setup login gagal mengurai JSON');
  }

  if (!body || !body.tokens || !body.tokens.access_token) {
    exec.test.abort('Setup login tidak mengembalikan token');
  }

  return {
    baseUrl: baseUrl,
    email: email,
    password: password,
    token: body.tokens.access_token,
    expiresIn: Number(body.tokens.expires_in) || 3600,
    issuedAtMs: Date.now(),
  };
}

// Cache per-VU untuk refresh token bila durasi skenario melebihi expires_in.
let vuToken = null;
let vuIssuedAtMs = 0;
let vuExpiresIn = 3600;

export function getValidToken(setupData) {
  if (!setupData || !setupData.token) {
    return '';
  }
  if (vuToken === null) {
    vuToken = setupData.token;
    vuIssuedAtMs = setupData.issuedAtMs || Date.now();
    vuExpiresIn = setupData.expiresIn || 3600;
  }

  const elapsedSec = (Date.now() - vuIssuedAtMs) / 1000;
  // Refresh 60 detik sebelum kedaluwarsa (atau bila sudah melewati expires_in)
  if (elapsedSec >= Math.max(vuExpiresIn - 60, 10)) {
    const loginPayload = JSON.stringify({
      email: setupData.email,
      password: setupData.password,
    });
    const res = http.post(`${setupData.baseUrl}/api/micro-cred/auth/login`, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
      tags: { phase: 'refresh' },
      timeout: '30s',
    });
    if (res.status === 200) {
      try {
        const body = res.json();
        if (body && body.tokens && body.tokens.access_token) {
          vuToken = body.tokens.access_token;
          vuExpiresIn = Number(body.tokens.expires_in) || 3600;
          vuIssuedAtMs = Date.now();
        }
      } catch (_) {
        // Pertahankan token sebelumnya bila gagal parse
      }
    }
  }
  return vuToken;
}

// Catat metrik hanya untuk tahap 'main' (mengabaikan warm-up 10 detik).
export function recordMainMetrics(res, expectedStatus = 200) {
  if (exec.scenario.name !== 'main') {
    return;
  }
  mainReqs.add(1);
  mainDuration.add(res.timings.duration);

  // status === 0 pada k6 menandakan request timeout / koneksi gagal di sisi klien
  const isTimeout = res.status === 0;
  mainTimeouts.add(isTimeout ? 1 : 0);

  const ok = Array.isArray(expectedStatus)
    ? expectedStatus.indexOf(res.status) !== -1
    : res.status === expectedStatus;
  mainFailed.add(ok ? 0 : 1);

  mainStatus200.add(res.status === 200 ? 1 : 0);
  mainStatus400.add(res.status === 400 ? 1 : 0);
  mainStatus401.add(res.status === 401 ? 1 : 0);
  mainStatus413.add(res.status === 413 ? 1 : 0);
  mainStatus503.add(res.status === 503 ? 1 : 0);
  mainStatus5xx.add(res.status >= 500 && res.status < 600 ? 1 : 0);
  mainStatusOther.add(
    res.status !== 200 &&
      res.status !== 400 &&
      res.status !== 401 &&
      res.status !== 413 &&
      !(res.status >= 500 && res.status < 600)
      ? 1
      : 0
  );
}
