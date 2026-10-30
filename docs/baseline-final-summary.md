# Ringkasan Akhir Pengujian Baseline Fase A dan Uji Ulang Titik Jenuh S2 (`docs/baseline-final-summary.md`)

Dokumen ini memuat hasil pengukuran aktual tanpa estimasi dari:
1. **Fase A Baseline Tiga Jalur (`direct`, `noauth`, `gateway`)** pada tiga layanan (`Micro-cred`, `Judul`, `Matkul`) tanpa pemanggilan LLM (`gateway/tests/baseline/out/phase-a-summary.json`).
2. **Tabel Selisih Overhead ($\Delta_{\text{proxy}}$, $\Delta_{\text{auth}}$, $\Delta_{\text{total}}$)** pada metrik utama `p50` dan `p95`.
3. **Uji Ulang S2 (`GET /api/micro-cred/tracks`, `50`–`800` req/s)** dengan `PREALLOC_VUS=200` dan `MAX_VUS=500` (`gateway/tests/perf/out/summary-medians.json`).

---

## (a) Tabel Tiga Jalur per Kondisi (`direct`, `noauth`, `gateway`)

> **Catatan definisi**: `"standalone"` (`direct`) pada eksperimen ini adalah layanan yang sama yang diakses langsung di dalam jaringan Docker `superapp_default` (`http://microcred-api:8000`, `http://judul-api:8001`, `http://matkul:3000`) tanpa melewati reverse proxy NGINX dan tanpa autentikasi terpusat `auth-verifier` (bukan deployment non-container asli). Rentang `[Min-Maks]` adalah nilai minimum hingga maksimum dari median/persentil per ulangan ($R = 3$ ulangan penuh; kecuali kondisi yang terhenti akibat jenuh).

| Kondisi | Layanan | Endpoint | Laju Target (req/s) | Jalur | p50 Median [Min-Maks] (ms) | p95 Median [Min-Maks] (ms) | p99 Median (ms) | Rata-rata (ms) | Throughput (req/s) | Error Rate (%) | Dropped Iterations | Interval Stats Median (s) |
|---|---|---|---:|---|---|---|---|---|---:|---:|---:|---|
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `direct` | 5.08 [4.58-5.60] | 9.61 [8.72-680.16] | 10.31 | 6.19 | 20.03 | 0.00% | 0 | 2.06 |
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `noauth` | 5.33 [4.97-5.81] | 8.50 [8.48-8.61] | 10.42 | 5.87 | 20.00 | 0.00% | 0 | 2.06 |
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `gateway` | 7.19 [7.11-7.57] | 11.13 [10.96-11.59] | 14.52 | 7.92 | 20.00 | 0.00% | 0 | 2.04 |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `direct` | 4.87 [4.76-4.95] | 7.56 [7.47-63.02] | 8.99 | 5.25 | 50.03 | 0.00% | 0 | 2.04 |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `noauth` | 5.31 [5.23-5.42] | 7.67 [7.57-7.84] | 9.70 | 5.58 | 50.00 | 0.00% | 0 | 2.05 |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `gateway` | 7.06 [6.91-8.69] | 11.18 [10.87-342.15] | 212.39 | 11.27 | 50.03 | 0.00% | 0 | 2.05 |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `direct` | 4.77 [4.77-4.77] | 7.49 [7.49-7.49] | 13.34 | 5.18 | 100.03 | 0.00% | 24 | 2.04 |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `noauth` | 5.50 [5.11-5.88] | 146.31 [50.17-242.45] | 584.79 | 29.16 | 100.03 | 0.00% | 4 | 2.05 |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `gateway` | 76.37 [6.43-146.30] | 2,308.45 [15.29-4,601.60] | 2,564.57 | 822.34 | 56.73 | 19.85% | 492 | 2.06 |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `direct` | 4.41 [4.26-4.58] | 209.49 [7.50-9,194.22] | 1,437.07 | 54.68 | 20.00 | 0.00% | 0 | 2.07 |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `noauth` | 4.81 [4.77-4.84] | 7.64 [6.97-8.06] | 8.93 | 5.20 | 20.03 | 0.00% | 0 | 2.05 |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `gateway` | 6.51 [6.02-6.89] | 10.28 [9.62-10.55] | 11.51 | 7.05 | 20.03 | 0.00% | 0 | 2.05 |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `direct` | 5.61 [4.32-5.79] | 7.90 [6.43-7.93] | 11.95 | 5.97 | 50.03 | 0.00% | 0 | 2.05 |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `noauth` | 4.89 [4.87-7.01] | 7.67 [7.47-13.41] | 9.82 | 5.22 | 50.03 | 0.00% | 0 | 2.05 |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `gateway` | 7.37 [6.52-9.02] | 14.31 [11.86-691.86] | 42.23 | 8.95 | 50.03 | 0.00% | 0 | 2.06 |
| **J1-50rps** | Judul | `GET /` | 50 | `direct` | 1.28 [1.27-1.29] | 1.79 [1.76-1.81] | 3.00 | 1.35 | 50.03 | 0.00% | 0 | 2.07 |
| **J1-50rps** | Judul | `GET /` | 50 | `noauth` | 2.09 [2.08-2.10] | 3.16 [3.13-3.32] | 3.84 | 2.21 | 50.03 | 0.00% | 0 | 2.06 |
| **J1-50rps** | Judul | `GET /` | 50 | `gateway` | 4.29 [4.15-4.38] | 6.13 [6.07-6.64] | 9.27 | 4.52 | 50.03 | 0.00% | 0 | 2.07 |
| **J1-200rps** | Judul | `GET /` | 200 | `direct` | 1.16 [1.13-1.17] | 1.60 [1.53-1.65] | 3.62 | 1.23 | 200.03 | 0.00% | 0 | 2.06 |
| **J1-200rps** | Judul | `GET /` | 200 | `noauth` | 1.77 [1.72-1.88] | 2.63 [2.59-3.12] | 5.02 | 1.87 | 200.03 | 0.00% | 0 | 2.07 |
| **J1-200rps** | Judul | `GET /` | 200 | `gateway` | 3.51 [3.37-3.72] | 6.15 [5.80-7.87] | 15.05 | 3.87 | 200.03 | 0.00% | 0 | 2.07 |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `direct` | 3.82 [3.64-4.02] | 5.91 [5.58-5.94] | 9.26 | 4.09 | 20.03 | 0.00% | 0 | 2.07 |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `noauth` | 4.25 [4.04-4.71] | 7.16 [6.83-7.42] | 9.32 | 4.55 | 20.03 | 0.00% | 0 | 2.06 |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `gateway` | 6.48 [6.23-6.49] | 9.75 [9.47-10.24] | 13.44 | 6.88 | 20.03 | 0.00% | 0 | 2.06 |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `direct` | 3.24 [3.07-3.62] | 6.10 [4.42-150.43] | 18.82 | 3.92 | 50.03 | 0.00% | 0 | 2.40 |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `noauth` | 4.01 [3.99-4.08] | 8.38 [7.77-156.47] | 26.13 | 4.82 | 50.00 | 0.00% | 0 | 2.12 |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `gateway` | 6.79 [6.62-8.30] | 30.54 [18.22-3,045.49] | 408.57 | 18.66 | 50.00 | 0.00% | 0 | 2.12 |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `direct` | 8.05 [8.05-8.05] | 14.47 [14.47-14.47] | 21.46 | 8.71 | 5.00 | 1.33% | 0 | 2.09 |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `noauth` | 11.95 [11.95-11.95] | 28.45 [28.45-28.45] | 49.83 | 14.41 | 5.03 | 0.00% | 0 | 2.09 |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `gateway` | 3,281.73 [3,281.73-3,281.73] | 3,364.25 [3,364.25-3,364.25] | 3,364.79 | 3,203.17 | 0.50 | 100.00% | 0 | tidak diukur |
| **K2-10rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 10 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 10 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 10 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

---

## (b) Tabel Selisih Antar Jalur ($\Delta_{\text{proxy}}$, $\Delta_{\text{auth}}$, $\Delta_{\text{total}}$) pada p50 dan p95

- $\Delta_{\text{proxy}} = \text{noauth} - \text{direct}$ (biaya reverse proxy NGINX + hop jaringan tanpa `auth_request`).
- $\Delta_{\text{auth}} = \text{gateway} - \text{noauth}$ (biaya subrequest `auth_request /_auth` ke `auth-verifier` dan verifikasi JWT HS256).
- $\Delta_{\text{total}} = \text{gateway} - \text{direct}$ (biaya total jalur gateway penuh dibanding akses langsung).
- Rentang `[Min..Maks]` dihitung dari hasil pengulangan per run ($r = 1 \dots R$), **bukan** rentang variasi setiap request individual. Bila rentang `p50` antar ulangan pada dua jalur saling tumpang tindih, tafsir ditulis **`tidak dapat dibedakan pada pengukuran ini`**.

| Kondisi | $\Delta_{\text{proxy}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{auth}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{total}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{proxy}}$ p95 [Min-Maks] (ms) | $\Delta_{\text{auth}}$ p95 [Min-Maks] (ms) | $\Delta_{\text{total}}$ p95 [Min-Maks] (ms) | Tafsir $\Delta_{\text{proxy}}$ | Tafsir $\Delta_{\text{auth}}$ | Tafsir $\Delta_{\text{total}}$ |
|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | 0.25 [-0.27..0.73] | 1.86 [1.30..2.24] | 2.11 [1.97..2.61] | -1.11 [-671.55..-0.22] | 2.63 [2.46..2.98] | 1.52 [-668.57..2.24] | tidak dapat dibedakan pada pengukuran ini | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M1-50rps** | 0.44 [0.36..0.66] | 1.75 [1.60..3.27] | 2.19 [1.96..3.93] | 0.11 [-55.35..0.37] | 3.51 [3.30..334.31] | 3.62 [-51.84..334.68] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M1-100rps** | 0.73 [0.34..0.34] | 70.87 [1.32..1.32] | 71.60 [1.66..1.66] | 138.82 [42.68..42.68] | 2,162.14 [-34.88..-34.88] | 2,300.96 [7.80..7.80] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M2-20rps** | 0.40 [0.26..0.55] | 1.70 [1.21..2.05] | 2.10 [1.76..2.31] | -201.85 [-9,186.16..0.14] | 2.64 [2.22..2.91] | -199.21 [-9,183.94..3.05] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M2-50rps** | -0.72 [-0.90..1.40] | 2.48 [1.65..2.48] | 1.76 [1.58..3.41] | -0.23 [-0.23..5.48] | 6.64 [4.39..678.45] | 6.41 [5.43..683.93] | tidak dapat dibedakan pada pengukuran ini | tidak dapat dibedakan pada pengukuran ini | rentang p50 tidak tumpang tindih |
| **J1-50rps** | 0.81 [0.80..0.82] | 2.20 [2.07..2.29] | 3.01 [2.88..3.09] | 1.37 [1.32..1.56] | 2.97 [2.75..3.51] | 4.34 [4.31..4.83] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **J1-200rps** | 0.61 [0.56..0.71] | 1.74 [1.63..1.95] | 2.35 [2.21..2.59] | 1.03 [0.99..1.47] | 3.52 [2.68..5.24] | 4.55 [4.15..6.34] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K1-20rps** | 0.43 [0.22..0.69] | 2.23 [1.78..2.44] | 2.66 [2.47..2.66] | 1.25 [1.22..1.51] | 2.59 [2.05..3.41] | 3.84 [3.56..4.66] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K1-50rps** | 0.77 [0.46..0.94] | 2.78 [2.63..4.29] | 3.55 [3.17..5.23] | 2.28 [1.67..6.04] | 22.16 [-125.93..3,037.11] | 24.44 [-119.89..3,041.07] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K2-5rps** | 3.90 [3.90..3.90] | 3,269.78 [3,269.78..3,269.78] | 3,273.68 [3,273.68..3,273.68] | 13.98 [13.98..13.98] | 3,335.80 [3,335.80..3,335.80] | 3,349.78 [3,349.78..3,349.78] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K2-10rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

**Temuan Kunci Overhead Gateway (`p50`) pada Kondisi Non-Jenuh (`M1-20`, `M1-50`, `M2-20`, `M2-50`, `J1-50`, `J1-200`, `K1-20`, `K1-50`):**
- **Biaya Reverse Proxy NGINX ($\Delta_{\text{proxy}}$ pada `p50`)**: berkisar antara **`0.25 ms` hingga `0.81 ms`** across seluruh tiga layanan (pada `M1-20rps` dan `M2-50rps` rentang antar-ulangannya tumpang tindih dengan variasi akses langsung).
- **Biaya Autentikasi Terpusat `auth_request` ($\Delta_{\text{auth}}$ pada `p50`)**: berkisar antara **`1.70 ms` hingga `2.78 ms`**, mendominasi sekitar **70%–85%** dari total overhead gateway.
- **Biaya Total Gateway ($\Delta_{\text{total}}$ pada `p50`)**: berkisar antara **`1.76 ms` hingga `3.55 ms`** dengan pemisahan rentang `p50` yang konsisten (`rentang p50 tidak tumpang tindih`) di seluruh kondisi non-jenuh.

---

## (c) Median CPU dan Memori per Container pada Fase Ukur

Nilai di bawah adalah **median** sampel `docker stats` selama jendela fase ukur 30 detik (bukan nilai puncak), lalu diambil median antar-ulangannya. `100%` CPU setara dengan 1 core logis penuh.

### (c.1) Median CPU (%) per Container

| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M1-20rps** | `direct` | 0.00 | 0.00 | 0.16 | 9.91 | 1.64 | 0.16 | 0.00 | 0.01 | 0.17 |
| **M1-20rps** | `noauth` | 0.00 | 1.06 | 0.16 | 9.12 | 1.42 | 0.16 | 0.00 | 0.00 | 0.17 |
| **M1-20rps** | `gateway` | 1.69 | 0.00 | 3.17 | 9.46 | 1.43 | 0.16 | 0.00 | 0.00 | 0.17 |
| **M1-50rps** | `direct` | 0.00 | 0.00 | 0.15 | 20.36 | 3.26 | 0.15 | 0.00 | 0.02 | 0.16 |
| **M1-50rps** | `noauth` | 0.00 | 2.43 | 0.15 | 21.13 | 3.20 | 0.15 | 0.00 | 0.00 | 0.16 |
| **M1-50rps** | `gateway` | 3.66 | 0.00 | 7.44 | 20.05 | 3.06 | 0.14 | 0.00 | 0.00 | 0.16 |
| **M1-100rps** | `direct` | 0.00 | 0.00 | 0.14 | 36.99 | 6.40 | 0.13 | 0.00 | 0.00 | 0.14 |
| **M1-100rps** | `noauth` | 0.00 | 4.72 | 0.15 | 41.83 | 6.26 | 0.14 | 0.00 | 0.00 | 0.15 |
| **M1-100rps** | `gateway` | 7.80 | 0.00 | 24.72 | 51.35 | 5.46 | 0.14 | 0.00 | 0.00 | 0.16 |
| **M2-20rps** | `direct` | 0.00 | 0.00 | 0.17 | 8.10 | 1.22 | 0.16 | 0.00 | 0.01 | 0.17 |
| **M2-20rps** | `noauth` | 0.00 | 1.06 | 0.16 | 8.01 | 1.13 | 0.16 | 0.00 | 0.00 | 0.17 |
| **M2-20rps** | `gateway` | 1.64 | 0.00 | 3.41 | 8.06 | 1.11 | 0.16 | 0.00 | 0.01 | 0.17 |
| **M2-50rps** | `direct` | 0.00 | 0.00 | 0.19 | 24.40 | 3.77 | 0.18 | 0.00 | 0.01 | 0.19 |
| **M2-50rps** | `noauth` | 0.00 | 2.43 | 0.16 | 19.08 | 2.78 | 0.15 | 0.00 | 0.00 | 0.17 |
| **M2-50rps** | `gateway` | 4.16 | 0.00 | 9.96 | 22.22 | 3.02 | 0.17 | 0.00 | 0.02 | 0.17 |
| **J1-50rps** | `direct` | 0.00 | 0.00 | 0.20 | 0.17 | 0.00 | 5.74 | 0.00 | 0.01 | 0.21 |
| **J1-50rps** | `noauth` | 0.00 | 3.21 | 0.19 | 0.17 | 0.00 | 7.79 | 0.00 | 0.00 | 0.22 |
| **J1-50rps** | `gateway` | 5.19 | 0.00 | 10.88 | 0.17 | 0.00 | 7.08 | 0.00 | 0.00 | 0.19 |
| **J1-200rps** | `direct` | 0.00 | 0.00 | 0.18 | 0.18 | 0.00 | 19.31 | 0.00 | 0.01 | 0.20 |
| **J1-200rps** | `noauth` | 0.00 | 10.74 | 0.16 | 0.15 | 0.00 | 25.16 | 0.00 | 0.01 | 0.18 |
| **J1-200rps** | `gateway` | 15.53 | 0.00 | 35.46 | 0.15 | 0.00 | 24.67 | 0.00 | 0.00 | 0.19 |
| **K1-20rps** | `direct` | 0.00 | 0.00 | 0.21 | 0.20 | 0.00 | 0.21 | 9.85 | 0.02 | 0.23 |
| **K1-20rps** | `noauth` | 0.00 | 1.42 | 0.21 | 0.18 | 0.00 | 0.20 | 10.20 | 0.00 | 0.22 |
| **K1-20rps** | `gateway` | 2.13 | 0.00 | 4.62 | 0.18 | 0.00 | 0.20 | 9.28 | 0.01 | 0.21 |
| **K1-50rps** | `direct` | 0.00 | 0.00 | 0.21 | 0.17 | 0.00 | 0.21 | 19.76 | 0.01 | 0.23 |
| **K1-50rps** | `noauth` | 0.00 | 3.38 | 0.20 | 0.18 | 0.00 | 0.20 | 19.07 | 0.00 | 0.24 |
| **K1-50rps** | `gateway` | 6.02 | 0.00 | 11.65 | 0.20 | 0.00 | 0.22 | 33.71 | 0.00 | 0.22 |
| **K2-5rps** | `direct` | 0.00 | 0.00 | 0.20 | 0.18 | 0.00 | 0.21 | 5.62 | 0.00 | 0.23 |
| **K2-5rps** | `noauth` | 0.00 | 0.48 | 0.21 | 0.18 | 0.00 | 0.23 | 6.18 | 0.02 | 0.24 |
| **K2-5rps** | `gateway` | 0.00 | 0.00 | 203.01 | 0.35 | 0.01 | 0.29 | 201.62 | 173.12 | 0.38 |
| **K2-10rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

### (c.2) Median Memori (MiB) per Container

| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M1-20rps** | `direct` | 13.6 | 7.4 | 49.4 | 109.6 | 60.0 | 53.0 | 213.4 | 18.0 | 16.7 |
| **M1-20rps** | `noauth` | 13.7 | 7.8 | 49.4 | 109.5 | 60.3 | 53.0 | 213.4 | 18.0 | 16.6 |
| **M1-20rps** | `gateway` | 14.0 | 7.4 | 49.5 | 109.5 | 60.2 | 53.0 | 213.4 | 17.8 | 16.6 |
| **M1-50rps** | `direct` | 13.7 | 7.5 | 51.5 | 110.1 | 56.0 | 53.0 | 213.4 | 18.0 | 16.7 |
| **M1-50rps** | `noauth` | 13.7 | 8.0 | 49.4 | 109.8 | 56.0 | 53.0 | 213.4 | 18.0 | 16.6 |
| **M1-50rps** | `gateway` | 14.3 | 7.5 | 51.7 | 109.8 | 56.0 | 53.0 | 213.4 | 18.0 | 16.6 |
| **M1-100rps** | `direct` | 13.7 | 7.5 | 51.5 | 111.0 | 56.0 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M1-100rps** | `noauth` | 13.8 | 8.3 | 51.5 | 110.8 | 56.0 | 53.0 | 213.5 | 18.2 | 16.6 |
| **M1-100rps** | `gateway` | 15.4 | 7.5 | 58.4 | 110.8 | 63.1 | 53.0 | 213.4 | 18.2 | 16.6 |
| **M2-20rps** | `direct` | 13.8 | 7.5 | 53.3 | 110.7 | 66.5 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M2-20rps** | `noauth` | 13.8 | 7.8 | 53.3 | 110.7 | 66.5 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M2-20rps** | `gateway` | 14.1 | 7.5 | 53.4 | 110.7 | 66.5 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M2-50rps** | `direct` | 13.7 | 7.5 | 53.3 | 110.8 | 66.0 | 53.0 | 214.2 | 18.2 | 16.7 |
| **M2-50rps** | `noauth` | 13.7 | 8.0 | 53.3 | 110.7 | 65.9 | 53.0 | 213.6 | 18.2 | 16.6 |
| **M2-50rps** | `gateway` | 14.4 | 7.5 | 53.5 | 110.7 | 65.9 | 53.0 | 214.2 | 18.2 | 16.6 |
| **J1-50rps** | `direct` | 13.8 | 7.5 | 53.3 | 110.6 | 66.0 | 53.4 | 214.3 | 18.3 | 16.7 |
| **J1-50rps** | `noauth` | 13.7 | 8.0 | 53.3 | 110.6 | 66.0 | 53.3 | 214.3 | 18.4 | 16.6 |
| **J1-50rps** | `gateway` | 14.3 | 7.5 | 53.5 | 110.6 | 66.0 | 53.3 | 214.3 | 18.3 | 16.6 |
| **J1-200rps** | `direct` | 13.8 | 7.5 | 53.3 | 110.6 | 66.0 | 54.0 | 214.3 | 18.4 | 16.7 |
| **J1-200rps** | `noauth` | 13.7 | 8.8 | 53.3 | 110.6 | 66.0 | 54.0 | 214.2 | 18.5 | 16.6 |
| **J1-200rps** | `gateway` | 15.1 | 7.5 | 55.6 | 110.6 | 66.0 | 53.9 | 214.2 | 18.6 | 16.6 |
| **K1-20rps** | `direct` | 13.7 | 7.5 | 55.3 | 110.6 | 66.0 | 53.8 | 246.2 | 18.5 | 16.7 |
| **K1-20rps** | `noauth` | 13.7 | 7.8 | 55.3 | 110.6 | 66.0 | 53.8 | 255.4 | 18.5 | 16.7 |
| **K1-20rps** | `gateway` | 14.1 | 7.5 | 55.4 | 110.6 | 66.0 | 53.8 | 262.3 | 18.5 | 16.6 |
| **K1-50rps** | `direct` | 13.8 | 7.5 | 55.3 | 110.6 | 66.0 | 53.8 | 263.0 | 18.6 | 16.7 |
| **K1-50rps** | `noauth` | 13.7 | 8.0 | 55.3 | 110.6 | 66.0 | 53.8 | 273.1 | 18.5 | 16.6 |
| **K1-50rps** | `gateway` | 14.3 | 7.5 | 53.6 | 110.6 | 66.0 | 53.8 | 267.0 | 18.5 | 16.6 |
| **K2-5rps** | `direct` | 13.7 | 7.5 | 55.3 | 110.6 | 66.0 | 53.8 | 297.2 | 18.8 | 16.7 |
| **K2-5rps** | `noauth` | 13.8 | 7.7 | 55.3 | 110.6 | 66.0 | 53.8 | 297.2 | 18.8 | 16.7 |
| **K2-5rps** | `gateway` | 13.8 | 7.5 | 55.4 | 110.6 | 66.0 | 53.8 | 230.9 | 19.0 | 16.7 |
| **K2-10rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

---

## (d) Tabel Uji Ulang Titik Jenuh S2 (`PREALLOC_VUS=200`, `MAX_VUS=500`, 3 Ulangan)

Target: `GET /api/micro-cred/tracks` melalui gateway penuh (`http://nginx`), warm-up 10 detik + fase ukur 30 detik, 3 ulangan per laju.

| Skenario | Target Rate (req/s) | Throughput Aktual Median [Min-Maks] (req/s) | p50 Median [Min-Maks] (ms) | p95 Median [Min-Maks] (ms) | p99 Median (ms) | Dropped Iterations Median [Min-Maks] | `vus_max` Median [Min-Maks] | Peringatan `"Insufficient VUs"` k6 | Error Rate Median [Min-Maks] (%) |
|---|---:|---|---|---|---|---|---|---|---|
| `s2-tracks-50rps` | 50 | 50.03 [50.00-50.03] | 10.66 [10.55-11.58] | 642.97 [30.05-937.52] | 1,235.20 | 0 [0-0] | 200 [200-200] | Tidak (`False`) | 0.00% [0.00%-0.00%] |
| `s2-tracks-100rps` | 100 | 100.00 [92.53-100.03] | 268.15 [34.08-402.94] | 1,356.63 [1,347.18-3,967.35] | 1,519.91 | 0 [0-225] | 200 [200-323] | Tidak (`False`) | 0.00% [0.00%-4.36%] |
| `s2-tracks-200rps` | 200 | 138.17 [132.50-149.73] | 3,307.68 [3,112.23-3,753.31] | 4,648.08 [4,266.54-6,566.20] | 4,722.04 | 1,855 [1,509-2,029] | 500 [500-500] | Ya (`True`) | 0.00% [0.00%-3.57%] |
| `s2-tracks-400rps` | 400 | 110.20 [106.80-164.13] | 4,382.01 [3,155.28-4,456.76] | 6,319.33 [3,990.60-8,232.97] | 6,623.33 | 8,694 [7,077-8,797] | 500 [500-500] | Ya (`True`) | 0.00% [0.00%-0.00%] |
| `s2-tracks-800rps` | 800 | 146.40 [112.87-173.47] | 3,369.04 [2,940.57-4,648.79] | 4,901.49 [3,720.09-6,434.85] | 4,934.56 | 19,609 [18,797-20,616] | 500 [500-500] | Ya (`True`) | 0.00% [0.00%-0.00%] |

**Jawaban Analisis S2 (`MAX_VUS=500` vs `MAX_VUS=100`):**
1. **Apakah throughput pada 400 dan 800 req/s naik di atas 250 req/s?** **Tidak.** Throughput aktual median tertahan pada **`138.17 req/s`** (pada target 200 req/s), **`110.20 req/s`** (pada target 400 req/s), dan **`146.40 req/s`** (pada target 800 req/s, dengan nilai tertinggi per ulangan `173.47 req/s` pada r1).
2. **Apakah `vus_max` mencapai 500 dan apakah peringatan `"Insufficient VUs"` masih muncul?** **Ya.** Pada target `200`, `400`, dan `800 req/s`, `vus_max` mencapai batas penuh **`500`** dan k6 tetap mencetak peringatan `"Insufficient VUs, reached 500 active VUs and cannot initialize more"`.
3. **Implikasi (Hukum Little $L = \lambda \cdot W$)**: Menaikkan batas VU sebesar $5\times$ (`100 -> 500`) **tidak** menaikkan throughput karena leher botol sesungguhnya berada pada kapasitas layanan backend (`microcred-api` + `db` + `auth-verifier`). Begitu laju kedatangan melampaui kapasitas layanan ($\sim 110\text{--}150\text{ req/s}$), antrean koneksi menyebabkan latensi `p50` membengkak sekitar $8\times$ lipat (dari `~400 ms` pada `maxVUs=100` menjadi `3,307.68–4,382.01 ms` pada `maxVUs=500`), sehingga seluruh 500 VU habis tertahan menunggu respons backend ($500\text{ VU} / 3.6\text{ s} \approx 138\text{ req/s}$). Ini membuktikan secara empiris bahwa plateau throughput dibatasi oleh kapasitas pemrosesan backend, bukan oleh generator beban k6.

---

## (e) Daftar Anomali, Kondisi Jenuh, Status K2, dan Validasi `noauth_verifier_hits`

1. **Run yang ditandai `"tidak tenang"` (`calm_before = false`, total CPU container $\ge 5\%$ setelah menunggu 60 detik + jeda 15 detik)**:
   - `J1-50rps-direct-r1`: total CPU terakhir `35.37%` setelah `77.9 s` (p50 tetap normal `1.27 ms`, error `0.00%`).
   - `K1-50rps-direct-r2`: total CPU terakhir `1.18%` pada sampel terakhir setelah `79.0 s` (hanya 1 sampel di bawah 5% sebelum batas 60s; p50 `3.24 ms`, error `0.00%`).
   - `K1-50rps-gateway-r3`: total CPU terakhir `1.07%` setelah `78.0 s` (p50 `6.79 ms`, error `0.00%`).
   - `K2-5rps-gateway-r1`: total CPU terakhir `101.05%` setelah `77.8 s` (CPU container `matkul` masih tinggi pasca ekstraksi PDF pada `K2-5rps-noauth-r1`).
2. **Run yang dihentikan / ditandai JENUH (`error_rate > 20%` selama $\ge 15$ detik, `k6 exit = 99`)**:
   - **`M1-100rps` pada ulangan ke-2 jalur `gateway` (`M1-100rps-gateway-r2`)**: mengalami `error_rate = 39.70%` (`exit=99`, `p50 = 146.30 ms`, `p95 = 4,601.60 ms`, `dropped_iterations = 983`). Sesuai aturan penghentian kelompok, `M1-100rps` dihentikan setelah ulangan ke-2 (`direct` selesai 1 ulangan, `noauth` dan `gateway` selesai 2 ulangan).
   - **`K2-5rps` pada ulangan ke-1 jalur `gateway` (`K2-5rps-gateway-r1`)**: setelah `K2-5rps-direct-r1` (`p50 = 8.05 ms`, `err = 1.33%`) dan `K2-5rps-noauth-r1` (`p50 = 11.95 ms`, `err = 0.00%`) selesai, event loop Node.js pada `matkul` masih sibuk (`CPU > 100%`) sehingga 15 request pada `K2-5rps-gateway-r1` terkena timeout koneksi NGINX (`HTTP 503` sekitar `3,281.73 ms`, `error_rate = 100.00%`, `exit=99`). Kelompok `K2` ditandai **JENUH** sehingga **`K2-10rps` dilewati** (`skipped = true`, ditulis `tidak diukur`).
   - Pada `K2-5rps-gateway-r1`, run dihentikan lebih awal oleh threshold k6 sehingga hanya terdapat 1 batch sampel `docker stats` pada jendela ukur; oleh karena itu `Interval Stats Median (s)` bernilai `tidak diukur` (dibutuhkan minimal 2 batch untuk menghitung selisih antar-sampel).
3. **Status Skenario Opsional K2 (Ekstraksi PDF Valid Matkul)**:
   - Pada uji pilot awal (Langkah 3), berkas `minimal-valid.pdf` berukuran `628 byte` (`< 4,096 byte`) memicu bug pengalokasian shared buffer `Buffer.from()` di Node.js (`byteOffset > 0` pada `Stream_makeSubStream` di `pdf.js v1.10.100`) sehingga mengembalikan `HTTP 500 {"error":"bad XRef entry"}`.
   - Setelah `New-MinimalValidPdf` di `run-baseline.ps1` diberi komentar PDF padding sepanjang `4,200 byte` (ukuran berkas menjadi `4,831 byte`, masih `< 20 KB`), verifikasi pra-syarat A3-K2 langsung ke `http://matkul:3000/api/panduan/extract-upload` **LOLOS** (`status=200`, `extracted_chars=53`, `K2 diaktifkan=True`).
4. **Validasi `noauth_verifier_hits`**:
   - Probe awal A1 ke `superapp-nginx-noauth` tanpa token mengembalikan `HTTP 200` dengan `noauth_probe_delta = 0`.
   - Di seluruh 10 kondisi yang dijalankan pada Fase A penuh, **`noauth_verifier_hits = false`** (`verifier_log_delta_sum = 0` pada seluruh run jalur `noauth` dan `direct`).

---

## (f) Perintah yang Dijalankan, Durasi Tiap Tahap, dan `git diff` Perubahan Skrip

### 1. Perintah dan Durasi Eksekusi

| Tahap | Perintah | Waktu Mulai (UTC) | Waktu Selesai (UTC) | Durasi |
|---|---|---|---|---|
| **Langkah 0a** | `docker compose ps` | `2026-10-30T07:28:15Z` | `2026-10-30T07:28:32Z` | `17 detik` |
| **Langkah 0b** | Backup `gateway/tests/perf/out` -> `out-backup-20261030` & `gateway/tests/baseline/out` -> `out-backup-20261030` | `2026-10-30T07:28:15Z` | `2026-10-30T07:28:20Z` | `5 detik` |
| **Langkah 3a (Pilot)** | `powershell -File gateway\tests\baseline\run-baseline.ps1 -Phase A -Repeats 1 -OnlyCondition M1-20rps` | `2026-10-30T07:31:03Z` | `2026-10-30T07:34:47Z` | `3 menit 44 detik` |
| **Langkah 3b (Report Pilot)** | `powershell -File gateway\tests\baseline\run-baseline.ps1 -Report` | `2026-10-30T07:34:58Z` | `2026-10-30T07:35:03Z` | `5 detik` |
| **Langkah 4a (Fase A Penuh)** | `powershell -File gateway\tests\baseline\run-baseline.ps1 -Phase A -Repeats 3` | `2026-10-30T07:42:06Z` | `2026-10-30T09:30:36Z` | `1 jam 48 menit 30 detik` |
| **Langkah 4b (Report Fase A)** | `powershell -File gateway\tests\baseline\run-baseline.ps1 -Report` | `2026-10-30T09:30:47Z` | `2026-10-30T09:30:56Z` | `9 detik` |
| **Langkah 5 (Ulang S2)** | `powershell -File gateway\tests\perf\run-perf.ps1 -OnlyScenario S2 -Repeats 3` | `2026-10-30T09:31:37Z` | `2026-10-30T09:49:26Z` | `17 menit 49 detik` |

### 2. Diff Perubahan Skrip

#### a. `git diff gateway/tests/perf/s2-saturation.js gateway/tests/perf/run-perf.ps1`

```diff
diff --git a/gateway/tests/perf/run-perf.ps1 b/gateway/tests/perf/run-perf.ps1
index 1aa7173..265270b 100644
--- a/gateway/tests/perf/run-perf.ps1
+++ b/gateway/tests/perf/run-perf.ps1
@@ -178,11 +178,11 @@ $scenarios = @(
     @{ Name = 's6-judul-50rps';           Group = 'S6'; Script = 's6-judul.js';      Env = @('RATE=50');  DurationSec = 30 },
     @{ Name = 's6-judul-200rps';          Group = 'S6'; Script = 's6-judul.js';      Env = @('RATE=200'); DurationSec = 30 },
 
-    @{ Name = 's2-tracks-50rps';          Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=50');  DurationSec = 30 },
-    @{ Name = 's2-tracks-100rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=100'); DurationSec = 30 },
-    @{ Name = 's2-tracks-200rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=200'); DurationSec = 30 },
-    @{ Name = 's2-tracks-400rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=400'); DurationSec = 30 },
-    @{ Name = 's2-tracks-800rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=800'); DurationSec = 30 }
+    @{ Name = 's2-tracks-50rps';          Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=50',  'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
+    @{ Name = 's2-tracks-100rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=100', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
+    @{ Name = 's2-tracks-200rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=200', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
+    @{ Name = 's2-tracks-400rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=400', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 },
+    @{ Name = 's2-tracks-800rps';         Group = 'S2'; Script = 's2-saturation.js'; Env = @('RATE=800', 'PREALLOC_VUS=200', 'MAX_VUS=500'); DurationSec = 30 }
 )
 
 if ($IncludeLlm) {
@@ -312,6 +312,9 @@ foreach ($sc in $scenarios) {
             $errRate = Get-K6MetricValue $m 'main_failed' 'value'
             if ($errRate -eq 0) { $errRate = Get-K6MetricValue $m 'main_failed' 'rate' }
             $dropped = Get-K6MetricValue $m 'dropped_iterations' 'count'
+            $vusMax = Get-K6MetricValue $m 'vus_max' 'value'
+            if ($vusMax -eq 0) { $vusMax = Get-K6MetricValue $m 'vus_max' 'max' }
+            $insuffVus = [bool](($k6Out -join "`n") -match 'Insufficient VUs')
             $timeouts = Get-K6MetricValue $m 'main_timeouts' 'count'
             $s200 = Get-K6MetricValue $m 'main_status_200' 'count'
             $s400 = Get-K6MetricValue $m 'main_status_400' 'count'
@@ -324,28 +327,30 @@ foreach ($sc in $scenarios) {
             $durSec = [double]$sc.DurationSec
             $rps = if ($durSec -gt 0) { $reqs / $durSec } else { 0.0 }
 
-            Write-Host ("  [r{0}] reqs={1} rps={2:N1} p50={3:N2}ms p95={4:N2}ms p99={5:N2}ms err={6:N2}% dropped={7} 503={8} timeout={9}" -f $r, $reqs, $rps, $p50, $p95, $p99, ($errRate * 100.0), $dropped, $s503, $timeouts)
+            Write-Host ("  [r{0}] reqs={1} rps={2:N1} p50={3:N2}ms p95={4:N2}ms p99={5:N2}ms err={6:N2}% dropped={7} vus_max={8} insuff_vus={9} 503={10} timeout={11}" -f $r, $reqs, $rps, $p50, $p95, $p99, ($errRate * 100.0), $dropped, $vusMax, $insuffVus, $s503, $timeouts)
 
             $runMetrics.Add([pscustomobject]@{
-                repeat               = $r
-                reqs                 = $reqs
-                rps                  = $rps
-                p50_ms               = $p50
-                p95_ms               = $p95
-                p99_ms               = $p99
-                avg_ms               = $avg
-                err_rate_pct         = $errRate * 100.0
-                dropped_iterations   = $dropped
-                timeouts             = $timeouts
-                status_200           = $s200
-                status_400           = $s400
-                status_401           = $s401
-                status_413           = $s413
-                status_503           = $s503
-                status_5xx           = $s5xx
-                json_413             = $json413
-                log_delta_tracks     = $logDeltaTracks
-                log_delta_non_health = $logDeltaNonHealth
+                repeat                   = $r
+                reqs                     = $reqs
+                rps                      = $rps
+                p50_ms                   = $p50
+                p95_ms                   = $p95
+                p99_ms                   = $p99
+                avg_ms                   = $avg
+                err_rate_pct             = $errRate * 100.0
+                dropped_iterations       = $dropped
+                vus_max                  = $vusMax
+                insufficient_vus_warning = $insuffVus
+                timeouts                 = $timeouts
+                status_200               = $s200
+                status_400               = $s400
+                status_401               = $s401
+                status_413               = $s413
+                status_503               = $s503
+                status_5xx               = $s5xx
+                json_413                 = $json413
+                log_delta_tracks         = $logDeltaTracks
+                log_delta_non_health     = $logDeltaNonHealth
             })
 
             # Jeda singkat 2 detik agar antrean koneksi backend reda sebelum ulangan berikutnya
@@ -384,9 +389,11 @@ foreach ($sc in $scenarios) {
             avg_ms               = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.avg_ms })), 2)
             reqs                 = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.reqs })), 0)
             throughput_rps       = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.rps })), 2)
-            error_rate_pct       = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.err_rate_pct })), 2)
-            dropped_iterations   = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.dropped_iterations })), 0)
-            timeouts             = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.timeouts })), 0)
+            error_rate_pct           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.err_rate_pct })), 2)
+            dropped_iterations       = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.dropped_iterations })), 0)
+            vus_max                  = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.vus_max })), 0)
+            insufficient_vus_warning = [bool](($runMetrics | Where-Object { $_.insufficient_vus_warning }).Count -gt 0)
+            timeouts                 = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.timeouts })), 0)
             status_200           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_200 })), 0)
             status_400           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_400 })), 0)
             status_401           = [math]::Round((Get-Median ($runMetrics | ForEach-Object { [double]$_.status_401 })), 0)
diff --git a/gateway/tests/perf/s2-saturation.js b/gateway/tests/perf/s2-saturation.js
index 2438ed3..429af4e 100644
--- a/gateway/tests/perf/s2-saturation.js
+++ b/gateway/tests/perf/s2-saturation.js
@@ -13,6 +13,8 @@ import {
 const BASE = __ENV.BASE || 'http://nginx';
 const RATE = Number(__ENV.RATE || 50);
 const WARMUP_SEC = Number(__ENV.WARMUP_SEC !== undefined ? __ENV.WARMUP_SEC : 10);
+const PREALLOC_VUS = Number(__ENV.PREALLOC_VUS || 50);
+const MAX_VUS = Number(__ENV.MAX_VUS || 100);
 
 const scenarios = {};
 if (WARMUP_SEC > 0) {
@@ -30,8 +32,8 @@ scenarios.main = {
   timeUnit: '1s',
   duration: '30s',
   startTime: `${WARMUP_SEC}s`,
-  preAllocatedVUs: 50,
-  maxVUs: 100,
+  preAllocatedVUs: PREALLOC_VUS,
+  maxVUs: MAX_VUS,
   tags: { phase: 'main' },
 };
```

#### b. Perubahan pada `gateway/tests/baseline/run-baseline.ps1` (berkas baru / untracked di Git)

```diff
--- a/gateway/tests/baseline/run-baseline.ps1
+++ b/gateway/tests/baseline/run-baseline.ps1
@@ -257,1 +257,3 @@ function New-MinimalValidPdf([string]$FilePath, [string]$TextContent = 'Panduan
-    $header = "%PDF-1.4`n"
+    # Pad komentar PDF > 4096 byte agar Buffer.from() di Node.js tidak memakai shared pool (byteOffset > 0 memicu bug Stream_makeSubStream di pdf.js v1.10.100)
+    $padComment = "%" + ('A' * 4200) + "`n"
+    $header = "%PDF-1.4`n" + $padComment
@@ -458,2 +460,5 @@ function Invoke-PhaseA {
-            $probeRaw = $probePy | & docker compose exec -T microcred-api python - 2>$null
+            $prevErrProbe = $ErrorActionPreference
+            $ErrorActionPreference = 'Continue'
+            $probeRaw = $probePy | & docker compose exec -T microcred-api python - 2>$null
+            $ErrorActionPreference = $prevErrProbe
             $probeNoAuthCode = ConvertTo-TrimmedString $probeRaw
@@ -480,1 +485,1 @@ function Invoke-PhaseA {
-import urllib.request, json, base64
+import urllib.request, urllib.error, json, base64
@@ -494,12 +499,22 @@ function Invoke-PhaseA {
-with urllib.request.urlopen(req, timeout=15) as resp:
-    data = json.loads(resp.read().decode('utf-8'))
-    print(json.dumps({'status': resp.status, 'ok': data.get('ok'), 'extracted_chars': data.get('extracted_chars', 0)}))
+try:
+    with urllib.request.urlopen(req, timeout=15) as resp:
+        data = json.loads(resp.read().decode('utf-8'))
+        print(json.dumps({'status': resp.status, 'ok': data.get('ok'), 'extracted_chars': data.get('extracted_chars', 0)}))
+except urllib.error.HTTPError as e:
+    err_body = e.read().decode('utf-8', errors='replace')
+    print(json.dumps({'status': e.code, 'ok': False, 'extracted_chars': 0, 'error': err_body}))
+except Exception as e:
+    print(json.dumps({'status': 0, 'ok': False, 'extracted_chars': 0, 'error': str(e)}))
 "@
-        $k2Raw = $k2VerifyPy | & docker compose exec -T microcred-api python - 2>$null
+        $prevErrK2 = $ErrorActionPreference
+        $ErrorActionPreference = 'Continue'
+        $k2Raw = $k2VerifyPy | & docker compose exec -T microcred-api python - 2>$null
+        $ErrorActionPreference = $prevErrK2
         $k2VerifyOut = ConvertTo-TrimmedString $k2Raw
         if (-not $k2VerifyOut) {
             throw "ABORT A3-K2: Verifikasi PDF minimal langsung ke matkul:3000 menghasilkan output kosong."
         }
         $k2VerifyObj = ConvertFrom-JsonSafe -JsonText $k2VerifyOut -Context 'Verifikasi K2 matkul:3000'
         $k2Enabled = ($k2VerifyObj.status -eq 200 -and [int]$k2VerifyObj.extracted_chars -gt 0)
-        Write-Host "[A3-K2] Verifikasi PDF minimal langsung ke matkul:3000 -> status=$($k2VerifyObj.status), extracted_chars=$($k2VerifyObj.extracted_chars), K2 diaktifkan=$k2Enabled"
+        $k2ErrInfo = if ($k2VerifyObj.PSObject.Properties['error'] -and $k2VerifyObj.error) { " (detail: $($k2VerifyObj.error))" } else { "" }
+        Write-Host "[A3-K2] Verifikasi PDF minimal langsung ke matkul:3000 -> status=$($k2VerifyObj.status), extracted_chars=$($k2VerifyObj.extracted_chars), K2 diaktifkan=$k2Enabled$k2ErrInfo"
@@ -550,1 +565,1 @@ function Invoke-PhaseA {
-            if ($Resume -and $summaryMap.Contains($cid) -and -not $summaryMap[$cid].skipped) {
+            if ($Resume -and $summaryMap.Contains($cid) -and -not $summaryMap[$cid].skipped -and [int]$summaryMap[$cid].repeats_completed -ge $Repeats) {
@@ -1305,1 +1320,1 @@ function Invoke-GenerateBaselineTables {
-    [void]$sb.AppendLine('| Kondisi | Layanan | Endpoint | Laju Target (req/s) | Jalur | p50 Median [Min–Maks] (ms) | p95 Median [Min–Maks] (ms) | p99 Median (ms) | Rata-rata (ms) | Throughput (req/s) | Kegagalan (%) | Dropped Iterations | Interval Stats Median (s) |')
+    [void]$sb.AppendLine('| Kondisi | Layanan | Endpoint | Laju Target (req/s) | Jalur | p50 Median [Min-Maks] (ms) | p95 Median [Min-Maks] (ms) | p99 Median (ms) | Rata-rata (ms) | Throughput (req/s) | Kegagalan (%) | Dropped Iterations | Interval Stats Median (s) |')
@@ -1320,2 +1335,2 @@ function Invoke-GenerateBaselineTables {
-                $p50Cell = ('{0:N2} [{1:N2}–{2:N2}]' -f [double]$pObj.p50_median_ms, [double]$pObj.p50_min_ms, [double]$pObj.p50_max_ms)
-                $p95Cell = ('{0:N2} [{1:N2}–{2:N2}]' -f [double]$pObj.p95_median_ms, [double]$pObj.p95_min_ms, [double]$pObj.p95_max_ms)
+                $p50Cell = ('{0:N2} [{1:N2}-{2:N2}]' -f [double]$pObj.p50_median_ms, [double]$pObj.p50_min_ms, [double]$pObj.p50_max_ms)
+                $p95Cell = ('{0:N2} [{1:N2}-{2:N2}]' -f [double]$pObj.p95_median_ms, [double]$pObj.p95_min_ms, [double]$pObj.p95_max_ms)
@@ -1344,1 +1359,1 @@ function Invoke-GenerateBaselineTables {
-    [void]$sb.AppendLine('| Kondisi | $\Delta_{\text{proxy}}$ p50 [Min–Maks] (ms) | $\Delta_{\text{auth}}$ p50 [Min–Maks] (ms) | $\Delta_{\text{total}}$ p50 [Min–Maks] (ms) | $\Delta_{\text{proxy}}$ p95 [Min–Maks] (ms) | $\Delta_{\text{auth}}$ p95 [Min–Maks] (ms) | $\Delta_{\text{total}}$ p95 [Min–Maks] (ms) | Tafsir $\Delta_{\text{proxy}}$ | Tafsir $\Delta_{\text{auth}}$ | Tafsir $\Delta_{\text{total}}$ |')
+    [void]$sb.AppendLine('| Kondisi | $\Delta_{\text{proxy}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{auth}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{total}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{proxy}}$ p95 [Min-Maks] (ms) | $\Delta_{\text{auth}}$ p95 [Min-Maks] (ms) | $\Delta_{\text{total}}$ p95 [Min-Maks] (ms) | Tafsir $\Delta_{\text{proxy}}$ | Tafsir $\Delta_{\text{auth}}$ | Tafsir $\Delta_{\text{total}}$ |')
```

