// S5: Uji upload file besar ke /api/matkul-recommender/panduan/extract-upload.
// MODE = '14m': file 14 MB bukan PDF dengan 1, 3, 5 VU selama 20s (harus 400 dari aplikasi Matkul).
// MODE = '17m': file 17 MB pada 20 req/s selama 30s (harus 413 JSON dari NGINX).
// Batas keras: tidak pernah melebihi 5 VU.

import http from 'k6/http';
import { Counter } from 'k6/metrics';
import exec from 'k6/execution';
import {
  SUMMARY_TREND_STATS,
  buildThresholds,
  getValidToken,
  recordMainMetrics,
  registerAndLogin,
} from './common.js';

const BASE = __ENV.BASE || 'http://nginx';
const MODE = (__ENV.MODE || '14m').toLowerCase();
const VUS = Math.min(Number(__ENV.VUS || 1), 5);
const RATE = Number(__ENV.RATE || 20);
const WARMUP_SEC = Number(__ENV.WARMUP_SEC !== undefined ? __ENV.WARMUP_SEC : 10);

const EXPECTED_STATUS = MODE === '17m' ? 413 : 400;
http.setResponseCallback(http.expectedStatuses(EXPECTED_STATUS));

const fileBin =
  MODE === '17m'
    ? open('/scripts/out/dummy-17mb.bin', 'b')
    : open('/scripts/out/dummy-14mb.bin', 'b');

const mainJson413 = new Counter('main_json_413');

const scenarios = {};
if (WARMUP_SEC > 0) {
  scenarios.warmup = {
    executor: 'constant-vus',
    vus: MODE === '17m' ? 2 : Math.min(VUS, 2),
    duration: `${WARMUP_SEC}s`,
    gracefulStop: '0s',
    tags: { phase: 'warmup' },
  };
}
if (MODE === '17m') {
  scenarios.main = {
    executor: 'constant-arrival-rate',
    rate: RATE,
    timeUnit: '1s',
    duration: '30s',
    startTime: `${WARMUP_SEC}s`,
    preAllocatedVUs: 5,
    maxVUs: 5,
    tags: { phase: 'main' },
  };
} else {
  scenarios.main = {
    executor: 'constant-vus',
    vus: VUS,
    duration: '20s',
    startTime: `${WARMUP_SEC}s`,
    tags: { phase: 'main' },
  };
}

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
  const formData = {
    file_pdf: http.file(fileBin, 'dummy-upload.bin', 'application/octet-stream'),
  };

  const res = http.post(
    `${BASE}/api/matkul-recommender/panduan/extract-upload`,
    formData,
    {
      headers: { Authorization: `Bearer ${token}` },
      timeout: '60s',
    }
  );

  recordMainMetrics(res, EXPECTED_STATUS);

  if (exec.scenario.name === 'main' && MODE === '17m') {
    const ct = (res.headers['Content-Type'] || res.headers['content-type'] || '').toLowerCase();
    const isJson = res.status === 413 && ct.indexOf('application/json') !== -1;
    mainJson413.add(isJson ? 1 : 0);
  }
}
