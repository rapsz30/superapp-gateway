// S6: Uji GET /api/judul-recommender/ dengan token pada RATE = 50 dan 200 req/s
// tanpa memanggil LLM (warm-up 10s + pengukuran 30s).

import http from 'k6/http';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  getValidToken,
  recordMainMetrics,
  registerAndLogin,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const RATE = Number(__ENV.RATE || 50);
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
  const token = getValidToken(data);
  const res = http.get(`${BASE}/api/judul-recommender/`, {
    headers: { Authorization: `Bearer ${token}` },
    timeout: '10s',
  });
  recordMainMetrics(res, 200);
}
