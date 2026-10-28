// Skrip k6 untuk skenario F9 (kekurangan CPU pada microcred-api: 30 req/s ke GET /api/micro-cred/tracks).
// Token diteruskan lewat environment variable K6_TOKEN dan tidak pernah dicetak.

import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE = __ENV.BASE || 'http://nginx';
const TOKEN = __ENV.K6_TOKEN || '';
const RATE = Number(__ENV.RATE || 30);
const DURATION = __ENV.DURATION || '40s';

const reqDuration = new Trend('f9_duration', true);
const reqFailed = new Rate('f9_failed');
const reqCount = new Counter('f9_reqs');

export const options = {
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(50)', 'p(90)', 'p(95)', 'p(99)'],
  scenarios: {
    main: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 30,
      maxVUs: 60,
    },
  },
};

export default function () {
  const res = http.get(`${BASE}/api/micro-cred/tracks`, {
    headers: { Authorization: `Bearer ${TOKEN}` },
    timeout: '15s',
  });
  reqCount.add(1);
  reqDuration.add(res.timings.duration);
  reqFailed.add(res.status === 200 ? 0 : 1);
}

