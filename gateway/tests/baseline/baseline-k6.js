// Skrip k6 terpadu untuk Fase A: Pembanding akses langsung (direct), NGINX tanpa auth (noauth),
// dan gateway penuh (gateway) pada tiga layanan SuperApp (Micro-cred, Judul, Matkul).
// Aturan keras:
// - Tidak memanggil LLM.
// - Header Authorization: Bearer <token> yang SAMA dikirim di ketiga jalur dan semua layanan.
// - Warm-up 10 detik (tags: { phase: 'warmup' }) tidak dihitung ke dalam submetrik utama.
// - Hanya fase ukur 30 detik (tags: { phase: 'main' }) yang dicatat ke main_* dan http_req_duration{phase:main}.
// - Token tidak pernah dicetak ke log atau disimpan di file ringkasan JSON.

import http from 'k6/http';
import exec from 'k6/execution';
import { Counter, Rate, Trend } from 'k6/metrics';

const COND = (__ENV.COND || 'M1').toUpperCase();
const PATH_MODE = (__ENV.PATH_MODE || 'direct').toLowerCase();
const RATE = Number(__ENV.RATE || 20);
const WARMUP_SEC = Number(__ENV.WARMUP_SEC !== undefined ? __ENV.WARMUP_SEC : 10);
const MEASURE_SEC = Number(__ENV.MEASURE_SEC !== undefined ? __ENV.MEASURE_SEC : 30);
const TOKEN = __ENV.TOKEN || '';

const EXPECTED_STATUS = COND === 'K1' ? 400 : 200;
http.setResponseCallback(http.expectedStatuses(EXPECTED_STATUS));

// Muat payload berkas uji di init context hanya untuk kondisi K1 / K2
const smallTxtBin = COND === 'K1' ? open('/scripts/out/small-nonpdf.txt', 'b') : null;
const smallPdfBin = COND === 'K2' ? open('/scripts/out/minimal-valid.pdf', 'b') : null;

export const mainDuration = new Trend('main_duration', true);
export const mainFailed = new Rate('main_failed');
export const mainReqs = new Counter('main_reqs');
export const mainTimeouts = new Counter('main_timeouts');
export const mainStatus200 = new Counter('main_status_200');
export const mainStatus400 = new Counter('main_status_400');
export const mainStatus401 = new Counter('main_status_401');
export const mainStatus503 = new Counter('main_status_503');
export const mainStatus5xx = new Counter('main_status_5xx');
export const mainStatusOther = new Counter('main_status_other');
export const mainExtractedOk = new Counter('main_extracted_ok');

export const SUMMARY_TREND_STATS = ['avg', 'min', 'med', 'max', 'p(50)', 'p(90)', 'p(95)', 'p(99)'];

const preAllocVUs = Math.min(Math.max(RATE, 30), 120);
const maxVUs = Math.min(Math.max(RATE * 2, 60), 250);

const scenarios = {};
if (WARMUP_SEC > 0) {
  scenarios.warmup = {
    executor: 'constant-arrival-rate',
    rate: RATE,
    timeUnit: '1s',
    duration: `${WARMUP_SEC}s`,
    preAllocatedVUs: preAllocVUs,
    maxVUs: maxVUs,
    gracefulStop: '0s',
    tags: { phase: 'warmup', cond: COND, path_mode: PATH_MODE },
  };
}
scenarios.main = {
  executor: 'constant-arrival-rate',
  rate: RATE,
  timeUnit: '1s',
  duration: `${MEASURE_SEC}s`,
  startTime: `${WARMUP_SEC}s`,
  preAllocatedVUs: preAllocVUs,
  maxVUs: maxVUs,
  tags: { phase: 'main', cond: COND, path_mode: PATH_MODE },
};

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: scenarios,
  thresholds: {
    'http_req_duration{phase:main}': ['max>=0'],
    'http_req_failed{phase:main}': ['rate<=1'],
    main_duration: ['max>=0'],
    main_failed: [
      { threshold: 'rate<=0.20', abortOnFail: true, delayAbortEval: '15s' },
    ],
  },
};

function resolveTargetUrl() {
  if (COND === 'M1') {
    if (PATH_MODE === 'direct') return 'http://microcred-api:8000/tracks';
    if (PATH_MODE === 'noauth') return 'http://superapp-nginx-noauth/api/micro-cred/tracks';
    return 'http://nginx/api/micro-cred/tracks';
  }
  if (COND === 'M2') {
    if (PATH_MODE === 'direct') return 'http://microcred-api:8000/auth/me';
    if (PATH_MODE === 'noauth') return 'http://superapp-nginx-noauth/api/micro-cred/auth/me';
    return 'http://nginx/api/micro-cred/auth/me';
  }
  if (COND === 'J1') {
    if (PATH_MODE === 'direct') return 'http://judul-api:8001/';
    if (PATH_MODE === 'noauth') return 'http://superapp-nginx-noauth/api/judul-recommender/';
    return 'http://nginx/api/judul-recommender/';
  }
  // K1 dan K2: Matkul extract-upload
  if (PATH_MODE === 'direct') return 'http://matkul:3000/api/panduan/extract-upload';
  if (PATH_MODE === 'noauth') return 'http://superapp-nginx-noauth/api/matkul-recommender/panduan/extract-upload';
  return 'http://nginx/api/matkul-recommender/panduan/extract-upload';
}

const TARGET_URL = resolveTargetUrl();

export default function () {
  // Header Authorization: Bearer <token> dikirim identik di semua jalur dan semua layanan
  const headers = {
    Authorization: `Bearer ${TOKEN}`,
  };

  let res;
  if (COND === 'K1') {
    const formData = {
      file_pdf: http.file(smallTxtBin, 'bukan-pdf.txt', 'text/plain'),
    };
    res = http.post(TARGET_URL, formData, { headers: headers, timeout: '15s' });
  } else if (COND === 'K2') {
    const formData = {
      file_pdf: http.file(smallPdfBin, 'minimal-valid.pdf', 'application/pdf'),
    };
    res = http.post(TARGET_URL, formData, { headers: headers, timeout: '15s' });
  } else {
    res = http.get(TARGET_URL, { headers: headers, timeout: '10s' });
  }

  // Hanya catat submetrik untuk fase ukur ('main')
  if (exec.scenario.name !== 'main') {
    return;
  }

  mainReqs.add(1);
  mainDuration.add(res.timings.duration);

  const isTimeout = res.status === 0;
  mainTimeouts.add(isTimeout ? 1 : 0);

  let ok = res.status === EXPECTED_STATUS;
  if (COND === 'K2' && ok) {
    let chars = 0;
    try {
      const body = res.json();
      chars = Number(body && body.extracted_chars ? body.extracted_chars : 0);
    } catch (_) {
      chars = 0;
    }
    if (chars > 0) {
      mainExtractedOk.add(1);
    } else {
      ok = false;
    }
  }

  mainFailed.add(ok ? 0 : 1);

  mainStatus200.add(res.status === 200 ? 1 : 0);
  mainStatus400.add(res.status === 400 ? 1 : 0);
  mainStatus401.add(res.status === 401 ? 1 : 0);
  mainStatus503.add(res.status === 503 ? 1 : 0);
  mainStatus5xx.add(res.status >= 500 && res.status < 600 ? 1 : 0);
  mainStatusOther.add(
    res.status !== 200 &&
      res.status !== 400 &&
      res.status !== 401 &&
      !(res.status >= 500 && res.status < 600)
      ? 1
      : 0
  );
}

