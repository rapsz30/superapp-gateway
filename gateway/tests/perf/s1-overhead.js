// S1: Dekomposisi overhead pada 100 req/s (warm-up 10s + pengukuran 30s).
// TARGET = a (/healthz), b (/api/micro-cred/tracks dengan token), c (microcred-api:8000/tracks langsung).

import http from 'k6/http';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  getValidToken,
  recordMainMetrics,
  registerAndLogin,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const DIRECT_MICROCRED = __ENV.DIRECT_MICROCRED || 'http://microcred-api:8000';
const TARGET = (__ENV.TARGET || 'b').toLowerCase();
const RATE = Number(__ENV.RATE || 100);
const WARMUP_SEC = Number(__ENV.WARMUP_SEC !== undefined ? __ENV.WARMUP_SEC : 10);

const scenarios = {};
if (WARMUP_SEC > 0) {
  scenarios.warmup = {
    executor: 'constant-vus',
    vus: 5,
    duration: `${WARMUP_SEC}s`,
    gracefulStop: '0s',
    tags: { phase: 'warmup' },
  };
}
scenarios.main = {
  executor: 'constant-arrival-rate',
  rate: RATE,
  timeUnit: '1s',
  duration: '30s',
  startTime: `${WARMUP_SEC}s`,
  preAllocatedVUs: 50,
  maxVUs: 100,
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
  let res;
  if (TARGET === 'a') {
    res = http.get(`${BASE}/healthz`, { timeout: '10s' });
  } else if (TARGET === 'c') {
    res = http.get(`${DIRECT_MICROCRED}/tracks`, { timeout: '10s' });
  } else {
    const token = getValidToken(data);
    res = http.get(`${BASE}/api/micro-cred/tracks`, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: '10s',
    });
  }
  recordMainMetrics(res, 200);
}
