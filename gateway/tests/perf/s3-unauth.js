// S3: Uji penolakan tanpa token (GET /api/micro-cred/tracks tanpa Authorization)
// pada laju RATE = 200 dan 800 req/s (warm-up 10s + pengukuran 30s).
// Harus mengembalikan 401 dari gateway tanpa meneruskan request ke microcred-api.

import http from 'k6/http';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  recordMainMetrics,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const RATE = Number(__ENV.RATE || 200);
const WARMUP_SEC = Number(__ENV.WARMUP_SEC !== undefined ? __ENV.WARMUP_SEC : 10);

// Status 401 adalah respons yang diharapkan pada skenario ini.
http.setResponseCallback(http.expectedStatuses(401));

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

export default function () {
  const res = http.get(`${BASE}/api/micro-cred/tracks`, { timeout: '10s' });
  recordMainMetrics(res, 401);
}
