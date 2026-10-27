// S4: Uji login (bcrypt) dengan 1, 3, 5, 10 VU selama 20 detik tiap tingkat
// (diawali warm-up 10 detik). Skenario ini mengukur beban CPU hashing bcrypt di Micro-cred.

import http from 'k6/http';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  recordMainMetrics,
  registerAndLogin,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const VUS = Number(__ENV.VUS || 1);
const WARMUP_SEC = Number(__ENV.WARMUP_SEC !== undefined ? __ENV.WARMUP_SEC : 10);

const scenarios = {};
if (WARMUP_SEC > 0) {
  scenarios.warmup = {
    executor: 'constant-vus',
    vus: Math.min(VUS, 2),
    duration: `${WARMUP_SEC}s`,
    gracefulStop: '0s',
    tags: { phase: 'warmup' },
  };
}
scenarios.main = {
  executor: 'constant-vus',
  vus: VUS,
  duration: '20s',
  startTime: `${WARMUP_SEC}s`,
  tags: { phase: 'main' },
};

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: scenarios,
  thresholds: buildThresholds(),
};

export function setup() {
  return registerAndLogin(BASE);
}

export default function (data) {
  const payload = JSON.stringify({
    email: data.email,
    password: data.password,
  });
  const res = http.post(`${BASE}/api/micro-cred/auth/login`, payload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',
  });
  recordMainMetrics(res, 200);
}
