# Laporan Pengujian Kinerja dan Beban Gateway SuperApp

Tanggal pengujian: **2026-10-27**  
Orkestrator: [`gateway/tests/perf/run-perf.ps1`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/run-perf.ps1) (`-Repeats 3`, `-IncludeLlm:$false`)  
Seluruh pengujian dijalankan di dalam jaringan Docker `superapp_default` menggunakan container `grafana/k6`. Tidak ada token, secret, atau data pribadi yang dicetak maupun disimpan di laporan ini atau di file hasil JSON.

---

## 1. Tujuan

1. Mengukur **overhead gateway NGINX dan verifikasi JWT (`auth-verifier`)** dibandingkan pemanggilan langsung ke layanan backend (**S1**).
2. Menentukan **titik jenuh (saturation point)** pada rute terproteksi `/api/micro-cred/tracks` dengan kriteria `p95 > 500 ms` atau `error rate > 1%`, serta mengamati gejala kegagalan pertama (**S2**).
3. Memastikan permintaan **tanpa token (`Authorization`)** ditolak cepat dengan `401` di tingkat gateway tanpa membebani `microcred-api` (**S3**).
4. Mengukur kapasitas dan latensi **login (`bcrypt`)** pada berbagai tingkat konkurensi VU (**S4**).
5. Menguji penanganan **unggah file besar** berukuran 14 MB (diteruskan ke aplikasi Matkul dan ditolak `400` karena bukan PDF) dan 17 MB (ditolak langsung `413` JSON oleh NGINX), serta memantau penggunaan memori container `matkul` dan `nginx` (**S5**).
6. Mengukur kinerja rute terproteksi ringan **`GET /api/judul-recommender/`** tanpa pemanggilan LLM (**S6**).

---

## 2. Lingkungan Pengujian

Spesifikasi perangkat keras dan perangkat lunak diambil dari `systeminfo`, `Win32_Processor`, dan `docker info` tanpa menyertakan identitas pribadi atau nama host:

| Komponen | Spesifikasi |
|---|---|
| Sistem Operasi Host | Microsoft Windows 11 Home Single Language, Versi `10.0.26200` (Build `26200`), x64 |
| Prosesor (CPU) | 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz (4 core fisik, 8 prosesor logis, maks 2419 MHz) |
| Memori Fisik Host | 7.883 MB (~7,70 GiB) |
| Docker Engine | Docker Desktop `29.8.0` (build `88096ef`), Kernel Linux `5.15.153.1-microsoft-standard-WSL2` |
| Alokasi Resource Docker (WSL2) | 8 vCPU (`NCPU=8`), RAM Total `4.016.869.376 byte` (~`3.831 MiB` / `3,74 GiB`) |
| Generator Beban | `grafana/k6:latest` (`sha256:3e4186aea62e11a45560bfc51e19eeafe82fc07ce069c78aff44b7ff893d9a5e`) |

### Daftar Container Layanan (`superapp`)

| Container | Image | Konfigurasi Proses Utama |
|---|---|---|
| `superapp-nginx-1` | `nginx:1.27-alpine` | `worker_processes auto; worker_connections 1024;` |
| `superapp-auth-verifier-1` | `superapp-auth-verifier` (Python 3.12-slim) | Uvicorn 1 worker (`--port 8100 --no-access-log`), PyJWT HS256 |
| `superapp-microcred-api-1` | `superapp-microcred-api` (Python 3.12.2-slim) | Uvicorn 1 worker (`--port 8000`), SQLAlchemy async (`QueuePool` default 5+10) |
| `superapp-microcred-worker-1` | `superapp-microcred-worker` | Worker RQ Python (`src.workers.worker`) |
| `superapp-db-1` | `postgres:15.5` | PostgreSQL 15.5 |
| `superapp-redis-1` | `redis:7.2` | Redis 7.2 |
| `superapp-judul-api-1` | `superapp-judul-api` | FastAPI / Uvicorn (`--port 8001`) |
| `superapp-matkul-1` | `superapp-matkul` | Next.js App Router (`--port 3000`) |
| `superapp-pocketbase-1` | `superapp-pocketbase` | PocketBase (`--port 8090`) |

---

## 3. Metode

1. **Eksekusi Container k6:** Setiap skenario dijalankan dengan perintah:
   ```powershell
   docker run --rm --network superapp_default -v "<path mutlak gateway/tests/perf>:/scripts" -e BASE=http://nginx grafana/k6 run --summary-export /scripts/out/<nama>.json /scripts/<file>.js
   ```
2. **Warm-up & Ulangan:** Setiap skenario diawali tahap **warm-up 10 detik** (`tags: { phase: 'warmup' }`) yang tidak dihitung ke dalam metrik pengukuran utama (`main_duration`, `main_failed`, `main_reqs`). Tahap pengukuran utama berjalan selama **30 detik** dengan executor `constant-arrival-rate` (`preAllocatedVUs: 50, maxVUs: 100`), kecuali S4 dan S5-14MB yang menggunakan `constant-vus` selama **20 detik** sesuai spesifikasi. Setiap skenario diulang **3 kali** (`-Repeats 3`) dengan jeda 2 detik antar-ulangan agar koneksi *in-flight* di backend terkuras bersih, lalu diambil nilai **median**.
3. **Manajemen Token Uji:** Fungsi `setup()` pada [`common.js`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/common.js) mendaftarkan dan meloginkan satu akun mahasiswa uji baru (`uji-perf-<timestamp>-<acak>@example.com`), membagikan token ke seluruh VU, dan melakukan login ulang otomatis apabila waktu berjalan mendekati `expires_in` (3600 detik). Objek `setup_data` dihapus secara otomatis dari seluruh file JSON keluaran.
4. **Aturan Penghentian Keras (Abort Rule):** Sebelum dan sesudah setiap ulangan, [`run-perf.ps1`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/run-perf.ps1) memeriksa status kesehatan seluruh 9 container. Selain itu, k6 dikonfigurasi dengan threshold `main_failed: [{ threshold: 'rate<=0.20', abortOnFail: true, delayAbortEval: '15s' }]` untuk menghentikan pengujian seketika apabila *error rate* melampaui 20% selama 15 detik berturut-turut.
5. **Pencatatan Resource Container:** Selama tiap skenario berjalan, [`collect-stats.ps1`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/collect-stats.ps1) mencatat `docker stats --no-stream` setiap 2 detik ke `gateway/tests/perf/out/stats-<skenario>.csv`.

---

## 4. Hasil Pengujian per Skenario (Median dari 3 Ulangan)

### Ringkasan Metrik Latensi, Throughput, dan Galat (S1–S6)

| Skenario | Target / Konfigurasi | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Avg (ms) | Error Rate (%) | Dropped Iterations | Catatan Status HTTP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **S1a** (`s1a-healthz-100rps`) | `GET http://nginx/healthz` @ 100 req/s | 100,03 | 0,38 | 0,53 | 0,63 | 0,40 | 0,00% | 0 | 100% HTTP `200` (3.001 req) |
| **S1b** (`s1b-gw-tracks-100rps`) | `GET http://nginx/api/micro-cred/tracks` (Bearer) @ 100 req/s | 99,73 | 7,12 | 50,12 | 514,19 | 24,44 | 0,00% | 8 | 100% HTTP `200` (2.992 req) |
| **S1c** (`s1c-direct-tracks-100rps`) | `GET http://microcred-api:8000/tracks` (langsung) @ 100 req/s | 99,67 | 4,72 | 12,25 | 609,40 | 22,87 | 0,00% | 10 | 100% HTTP `200` (2.990 req) |
| **S2-50** (`s2-tracks-50rps`) | Target `b` @ 50 req/s | 50,03 | 6,98 | 10,07 | 14,53 | 7,57 | 0,00% | 0 | 100% HTTP `200` (1.501 req) — **Lolos** |
| **S2-100** (`s2-tracks-100rps`) | Target `b` @ 100 req/s | 99,40 | 7,31 | 480,49 | 657,48 | 65,45 | 0,00% | 19 | 100% HTTP `200` (2.982 req) — **Lolos (Ambang)** |
| **S2-200** (`s2-tracks-200rps`) | Target `b` @ 200 req/s | 194,30 | 208,86 | 513,86 | 810,93 | 220,83 | 0,00% | 172 | 100% HTTP `200` (5.829 req) — **Jenuh (`p95 > 500 ms`)** |
| **S2-400** (`s2-tracks-400rps`) | Target `b` @ 400 req/s | 243,60 | 392,48 | 505,87 | 583,15 | 408,09 | 0,00% | 4.693 | 100% HTTP `200` (7.308 req) — **Jenuh** |
| **S2-800** (`s2-tracks-800rps`) | Target `b` @ 800 req/s | 229,67 | 408,87 | 595,76 | 677,18 | 435,15 | 0,00% | 17.111 | 100% HTTP `200` (6.890 req) — **Jenuh** |
| **S3-200** (`s3-unauth-200rps`) | `GET /api/micro-cred/tracks` tanpa token @ 200 req/s | 200,03 | 1,58 | 2,21 | 2,84 | 1,62 | 0,00% | 0 | 100% HTTP `401` (6.001 req), Δ log `microcred-api` = 0 |
| **S3-800** (`s3-unauth-800rps`) | `GET /api/micro-cred/tracks` tanpa token @ 800 req/s | 792,10 | 1,34 | 22,07 | 127,79 | 6,50 | 0,00% | 238 | 100% HTTP `401` (23.763 req), Δ log `microcred-api` = 0 |
| **S4-1VU** (`s4-login-1vu`) | `POST /api/micro-cred/auth/login` (1 VU, 20s) | 3,75 | 258,23 | 327,19 | 381,68 | 267,05 | 0,00% | 0 | 100% HTTP `200` (75 req) |
| **S4-3VU** (`s4-login-3vu`) | `POST /api/micro-cred/auth/login` (3 VU, 20s) | 3,85 | 772,00 | 1.265,54 | 1.396,20 | 796,24 | 0,00% | 0 | 100% HTTP `200` (77 req) |
| **S4-5VU** (`s4-login-5vu`) | `POST /api/micro-cred/auth/login` (5 VU, 20s) | 4,00 | 1.247,68 | 1.781,66 | 2.110,55 | 1.276,64 | 0,00% | 0 | 100% HTTP `200` (80 req) |
| **S4-10VU** (`s4-login-10vu`) | `POST /api/micro-cred/auth/login` (10 VU, 20s) | 3,90 | 2.561,58 | 4.820,41 | 4.941,23 | 2.718,30 | 0,00% | 0 | 100% HTTP `200` (78 req) |
| **S5-14M-1VU** (`s5-upload14m-1vu`) | Upload 14 MB non-PDF ke Matkul (1 VU, 20s) | 16,45 | 50,74 | 77,42 | 103,84 | 54,74 | 0,00% | 0 | 100% HTTP `400` dari Matkul (329 req) |
| **S5-14M-3VU** (`s5-upload14m-3vu`) | Upload 14 MB non-PDF ke Matkul (3 VU, 20s) | 25,65 | 106,31 | 168,71 | 235,07 | 111,23 | 0,00% | 0 | 100% HTTP `400` dari Matkul (513 req) |
| **S5-14M-5VU** (`s5-upload14m-5vu`) | Upload 14 MB non-PDF ke Matkul (5 VU, 20s) | 25,15 | 181,00 | 291,23 | 376,87 | 192,28 | 0,00% | 0 | 100% HTTP `400` dari Matkul (503 req) |
| **S5-17M-20** (`s5-upload17m-20rps`) | Upload 17 MB ke Matkul @ 20 req/s (30s) | 20,03 | 0,13 | 8,67 | 10,91 | 1,88 | 0,00% | 0 | 100% HTTP `413` JSON dari NGINX (601/601 JSON) |
| **S6-50** (`s6-judul-50rps`) | `GET /api/judul-recommender/` (Bearer) @ 50 req/s | 50,00 | 3,07 | 4,81 | 5,65 | 3,29 | 0,00% | 0 | 100% HTTP `200` (1.500 req) |
| **S6-200** (`s6-judul-200rps`) | `GET /api/judul-recommender/` (Bearer) @ 200 req/s | 200,03 | 2,66 | 3,71 | 6,08 | 2,84 | 0,00% | 0 | 100% HTTP `200` (6.001 req) |

> [!NOTE]
> Pada S3 (`401`), S5-14MB (`400`), dan S5-17MB (`413`), kode status tersebut adalah respons penolakan yang diharapkan sesuai desain, sehingga `Error Rate (%)` mengukur proporsi respons yang menyimpang dari kode status yang diharapkan (seluruhnya `0,00%`).

---

### Puncak Penggunaan CPU (%) dan Memori (MiB) per Container

Nilai di bawah adalah puncak CPU (`%`, di mana `100%` setara 1 core logis penuh dari 8 core logis) dan puncak memori (`MiB`) yang tercatat oleh `docker stats --no-stream` (interval 2 detik) selama tiap skenario:

| Skenario | `nginx` (CPU / Mem) | `auth-verifier` (CPU / Mem) | `microcred-api` (CPU / Mem) | `db` (CPU / Mem) | `matkul` (CPU / Mem) | `judul-api` (CPU / Mem) | `microcred-worker` (CPU / Mem) | `redis` (CPU / Mem) | `pocketbase` (CPU / Mem) |
|---|---|---|---|---|---|---|---|---|---|
| **S1a** (`healthz` 100 rps) | 71,98% / 10,6 MiB | 36,44% / 63,4 MiB | 24,34% / 131,9 MiB | 27,24% / 67,7 MiB | 51,45% / 224,7 MiB | 44,69% / 65,7 MiB | 0,35% / 76,2 MiB | 5,35% / 20,9 MiB | 12,19% / 15,9 MiB |
| **S1b** (`gw-tracks` 100 rps) | 116,06% / 12,5 MiB | 100,59% / 67,6 MiB | 100,81% / 132,1 MiB | 124,99% / 76,4 MiB | 26,01% / 207,2 MiB | 42,43% / 52,7 MiB | 0,24% / 76,2 MiB | 7,82% / 16,5 MiB | 4,96% / 15,8 MiB |
| **S1c** (`direct-tracks` 100 rps) | 7,29% / 11,1 MiB | 55,82% / 53,4 MiB | 101,20% / 132,4 MiB | 17,19% / 65,5 MiB | 16,26% / 214,6 MiB | 0,21% / 52,6 MiB | 0,19% / 76,2 MiB | 3,28% / 16,6 MiB | 3,44% / 15,7 MiB |
| **S2-50** (`tracks` 50 rps) | 16,03% / 12,3 MiB | 67,41% / 58,0 MiB | 99,60% / 137,7 MiB | 15,77% / 68,0 MiB | 0,14% / 402,4 MiB | 32,07% / 52,7 MiB | 0,14% / 76,3 MiB | 4,29% / 16,8 MiB | 3,50% / 16,1 MiB |
| **S2-100** (`tracks` 100 rps) | 21,38% / 13,3 MiB | 77,26% / 58,2 MiB | 137,03% / 137,7 MiB | 22,44% / 79,6 MiB | 55,26% / 403,3 MiB | 38,93% / 52,8 MiB | 0,20% / 76,3 MiB | 0,31% / 16,6 MiB | 4,72% / 16,2 MiB |
| **S2-200** (`tracks` 200 rps) | 44,21% / 14,9 MiB | 72,29% / 62,6 MiB | 118,17% / 150,3 MiB | 23,82% / 75,4 MiB | 64,19% / 402,4 MiB | 71,68% / 52,7 MiB | 0,16% / 76,3 MiB | 4,84% / 16,6 MiB | 7,17% / 16,1 MiB |
| **S2-400** (`tracks` 400 rps) | 15,21% / 15,6 MiB | 71,62% / 67,8 MiB | 123,58% / 137,6 MiB | 21,79% / 78,3 MiB | 0,02% / 402,4 MiB | 32,40% / 57,8 MiB | 0,18% / 76,3 MiB | 3,39% / 16,5 MiB | 8,34% / 16,7 MiB |
| **S2-800** (`tracks` 800 rps) | 16,26% / 15,6 MiB | 87,22% / 66,5 MiB | 132,46% / 150,1 MiB | 22,76% / 79,8 MiB | 29,05% / 402,4 MiB | 43,86% / 64,2 MiB | 0,18% / 76,3 MiB | 8,47% / 16,9 MiB | 3,22% / 16,3 MiB |
| **S3-200** (`unauth` 200 rps) | 31,32% / 11,6 MiB | 144,78% / 63,9 MiB | 30,54% / 132,2 MiB | 8,56% / 57,3 MiB | 25,00% / 208,5 MiB | 29,29% / 64,6 MiB | 4,53% / 76,2 MiB | 2,69% / 16,6 MiB | 5,05% / 16,1 MiB |
| **S3-800** (`unauth` 800 rps) | 37,55% / 14,3 MiB | 134,93% / 69,0 MiB | 40,80% / 141,9 MiB | 24,30% / 59,2 MiB | 47,30% / 208,0 MiB | 41,12% / 52,8 MiB | 0,55% / 76,2 MiB | 8,65% / 16,8 MiB | 7,99% / 16,2 MiB |
| **S4-1VU** (`login` 1 VU) | 3,03% / 11,1 MiB | 59,59% / 63,6 MiB | 146,76% / 133,4 MiB | 22,64% / 73,9 MiB | 48,80% / 207,6 MiB | 41,40% / 52,7 MiB | 0,20% / 76,2 MiB | 4,82% / 16,6 MiB | 3,27% / 16,7 MiB |
| **S4-3VU** (`login` 3 VU) | 3,64% / 10,6 MiB | 47,64% / 68,4 MiB | 129,97% / 149,3 MiB | 8,58% / 74,8 MiB | 8,57% / 209,3 MiB | 35,72% / 65,9 MiB | 0,16% / 76,3 MiB | 0,27% / 16,8 MiB | 3,93% / 16,0 MiB |
| **S4-5VU** (`login` 5 VU) | 3,09% / 10,6 MiB | 32,80% / 57,0 MiB | 121,19% / 149,2 MiB | 7,08% / 75,5 MiB | 11,93% / 208,5 MiB | 18,51% / 62,8 MiB | 0,15% / 76,3 MiB | 2,57% / 16,6 MiB | 6,60% / 15,8 MiB |
| **S4-10VU** (`login` 10 VU) | 4,63% / 10,8 MiB | 28,04% / 56,8 MiB | 122,08% / 149,1 MiB | 16,25% / 85,9 MiB | 28,59% / 222,9 MiB | 33,45% / 62,6 MiB | 0,94% / 76,3 MiB | 3,25% / 16,8 MiB | 4,92% / 15,7 MiB |
| **S5-14M-1VU** (`upload` 14M 1 VU) | 71,08% / 11,2 MiB | 55,18% / 69,6 MiB | 6,51% / 136,3 MiB | 10,92% / 67,2 MiB | **222,98% / 298,0 MiB** | 61,12% / 52,7 MiB | 0,43% / 76,3 MiB | 7,28% / 16,6 MiB | 7,57% / 15,8 MiB |
| **S5-14M-3VU** (`upload` 14M 3 VU) | 112,52% / 15,0 MiB | 52,75% / 68,3 MiB | 61,94% / 147,8 MiB | 9,34% / 67,4 MiB | **282,77% / 389,8 MiB** | 59,14% / 52,7 MiB | 0,74% / 76,3 MiB | 4,01% / 16,8 MiB | 9,95% / 15,8 MiB |
| **S5-14M-5VU** (`upload` 14M 5 VU) | 120,90% / **20,8 MiB** | 70,20% / 68,3 MiB | 16,07% / 136,3 MiB | 23,77% / 67,4 MiB | **285,17% / 429,5 MiB** | 83,81% / 65,8 MiB | 0,47% / 76,3 MiB | 3,97% / 16,5 MiB | 4,33% / 16,1 MiB |
| **S5-17M-20** (`upload` 17M 20 rps) | 17,38% / **10,8 MiB** | 75,92% / 56,7 MiB | 53,62% / 149,3 MiB | 10,96% / 68,0 MiB | 21,75% / 402,5 MiB | 101,04% / 57,8 MiB | 0,31% / 76,3 MiB | 6,15% / 22,4 MiB | 10,31% / 15,8 MiB |
| **S6-50** (`judul` 50 rps) | 36,48% / 12,2 MiB | 121,05% / 67,8 MiB | 67,84% / 137,3 MiB | 9,17% / 67,7 MiB | 0,01% / 402,4 MiB | 90,95% / 62,8 MiB | 0,20% / 76,3 MiB | 2,68% / 16,5 MiB | 5,18% / 16,3 MiB |
| **S6-200** (`judul` 200 rps) | 39,56% / 12,6 MiB | 104,86% / 69,8 MiB | 40,14% / 137,3 MiB | 12,70% / 67,2 MiB | 15,53% / 402,4 MiB | 65,78% / 52,9 MiB | 0,20% / 76,3 MiB | 3,88% / 16,5 MiB | 3,31% / 16,0 MiB |

*(Catatan: Container yang tidak menjadi target langsung pada suatu skenario tetap memiliki aktivitas CPU periodik dari Docker healthcheck tiap 10–15 detik.)*

---

## 5. Analisis Mendalam per Skenario

### A. Hitungan Overhead Gateway dan Autentikasi (S1 pada 100 req/s)

| Komponen | p50 (ms) | p95 (ms) | p99 (ms) | Avg (ms) | Interpretasi |
|---|---:|---:|---:|---:|---|
| **a)** Biaya NGINX murni (`GET /healthz`) | `0,38` | `0,53` | `0,63` | `0,40` | Penanganan HTTP di NGINX tanpa upstream maupun `auth_request` memerlukan waktu sub-milidetik. |
| **b)** Lewat Gateway + Verifier (`GET /api/micro-cred/tracks`) | `7,12` | `50,12` | `514,19` | `24,44` | Mencakup NGINX, subrequest `/_auth` ke `auth-verifier`, penerusan proxy, verifikasi token lapis kedua di `microcred-api`, dan 2 kueri SQL ke PostgreSQL. |
| **c)** Langsung ke `microcred-api:8000/tracks` | `4,72` | `12,25` | `609,40` | `22,87` | Biaya murni aplikasi `microcred-api` + PostgreSQL pada laju 100 req/s. |
| **Selisih `b - c` (Overhead Gateway + Autentikasi)** | **`+2,40`** | **`+37,87`** | **`-95,21`** | **`+1,57`** | Pada median (`p50`), overhead total gateway + subrequest JWT `auth-verifier` hanya **`2,40 ms`** (`0,38 ms` biaya dasar NGINX + `~2,02 ms` subrequest `/_auth` & proxy). |

- **Mengapa `p99` pada `c` (`609,40 ms`) sedikit lebih tinggi dari `b` (`514,19 ms`)?**  
  Pada laju 100 req/s, `microcred-api` (1 worker Uvicorn + 2 kueri database per request) sudah beroperasi mendekati batas kapasitas CPU 1 core (`~101%` CPU). Akibatnya, ekor distribusi (`p95` dan `p99`) didominasi oleh antrean *event loop* dan *connection pool* SQLAlchemy di `microcred-api`, bukan oleh gateway. Hal ini terkonfirmasi pada skenario **S6** (`GET /api/judul-recommender/` pada 200 req/s), di mana jalur NGINX + `auth-verifier` + `judul-api` menghasilkan `p50 = 2,66 ms`, `p95 = 3,71 ms`, dan `p99 = 6,08 ms`.

---

### B. Titik Jenuh Target `b` (`GET /api/micro-cred/tracks` dengan Token — S2)

Kriteria jenuh: **`p95 > 500 ms`** atau **`error rate > 1%`**.

1. **Laju tertinggi yang lolos:**
   - Pada **50 req/s**, sistem sangat stabil (`p50 = 6,98 ms`, `p95 = 10,07 ms`, `p99 = 14,53 ms`, `error rate = 0%`, `dropped_iterations = 0`).
   - Pada **100 req/s**, median 3 ulangan masih **lolos tipis** (`p95 = 480,49 ms <= 500 ms`, `error rate = 0%`), namun tanda awal kejenuhan sudah mulai muncul berupa `dropped_iterations = 19` (dan pada ulangan ke-3, `p95` mencapai `641,75 ms`). Dengan demikian, **100 req/s adalah laju tertinggi yang lolos secara median**, sedangkan **50 req/s adalah laju tertinggi yang lolos bersih tanpa `dropped_iterations`**.
2. **Titik jenuh dan tanda kegagalan pertama:**
   - Pada **200 req/s**, target resmi **jenuh**: median `p95` naik menjadi **`513,86 ms`** (melampaui batas 500 ms), `p50` melonjak dari `7,31 ms` ke `208,86 ms`, dan muncul **`dropped_iterations` sebanyak 172** karena seluruh 100 VU mulai tertahan menunggu respons dari worker tunggal `microcred-api`.
   - Pada **400 req/s** dan **800 req/s**, throughput aktual mencapai plafon (plateau) di kisaran **`229,67–243,60 req/s`** sementara `dropped_iterations` melonjak ke **4.693** (pada 400 req/s) dan **17.111** (pada 800 req/s). Seluruh permintaan yang berhasil dikirim tetap dijawab `200 OK` (`error rate = 0%`, `timeout = 0`) selama terdapat jeda kuras 2 detik antar-ulangan.
3. **Temuan Penting Saat Transisi Tanpa Jeda Kuras (Efek Domino `proxy_read_timeout 3s` pada `/_auth`):**
   - Pada percobaan awal sebelum penambahan jeda kuras 2 detik antar-ulangan, ketika `s2-tracks-400rps` langsung dijalankan tepat setelah 90 detik beban `s2-tracks-200rps` sementara 100 permintaan *in-flight* di `microcred-api` belum selesai dikuras, kontensi CPU pada mesin uji membuat subrequest `/_auth` ke `auth-verifier` melampaui `proxy_read_timeout 3s` di [`nginx.conf`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/nginx/nginx.conf#L153-L154).
   - Akibatnya, NGINX mengaktifkan aturan *fail-closed* (`error_page 500 =503 @err_500`) dan mengembalikan **HTTP `503` (`{"detail":"Layanan autentikasi tidak tersedia"}`)** sebanyak 60 dari 93 permintaan (`64,52%`), yang langsung memicu penghentian otomatis k6 (`exit code 99`) setelah 15 detik. Temuan ini membuktikan bahwa mekanisme *fail-closed* gateway dan penghentian otomatis (>20% galat selama 15 detik) bekerja sesuai rancangan.

---

### C. Penolakan Tanpa Token (S3 pada 200 dan 800 req/s)

- Pada **200 req/s**, gateway menolak seluruh **6.001 permintaan** dengan status **`401`** (`error rate = 0%`, `dropped_iterations = 0`) dengan latensi **`p50 = 1,58 ms`**, **`p95 = 2,21 ms`**, dan **`p99 = 2,84 ms`**.
- Pada **800 req/s**, gateway mencapai throughput **792,10 req/s** (23.763 permintaan ditolak `401` per 30 detik, `error rate = 0%`) dengan **`p50 = 1,34 ms`**, **`p95 = 22,07 ms`**, dan **`p99 = 127,79 ms`**.
- **Verifikasi isolasi backend:** Pemeriksaan log `superapp-microcred-api-1` sebelum dan sesudah S3 menunjukkan **pertambahan baris akses `/tracks` adalah `0`** (`log_delta_tracks = 0`) dan **pertambahan baris non-healthcheck adalah `0`** (`log_delta_non_health = 0`) baik pada 200 req/s maupun 800 req/s. Seluruh beban tanpa token dihentikan oleh NGINX + `auth-verifier` tanpa menyentuh `microcred-api`.

---

### D. Kinerja Login Bcrypt (S4 pada 1, 3, 5, 10 VU)

- Skenario ini mengukur biaya komputasi hashing **`bcrypt` (cost 12)** di `microcred-api`, **bukan overhead gateway**.
- Throughput pada 1, 3, 5, dan 10 VU bersifat **datar (konstan) di kisaran `3,75–4,00 req/s`**:
  - **1 VU:** `3,75 req/s`, `p50 = 258,23 ms`, `p95 = 327,19 ms`
  - **3 VU:** `3,85 req/s`, `p50 = 772,00 ms`, `p95 = 1.265,54 ms`
  - **5 VU:** `4,00 req/s`, `p50 = 1.247,68 ms`, `p95 = 1.781,66 ms`
  - **10 VU:** `3,90 req/s`, `p50 = 2.561,58 ms`, `p95 = 4.820,41 ms`
- **Penyebab:** Satu operasi verifikasi `bcrypt` (cost 12) membutuhkan waktu CPU murni sekitar `~250 ms`. Karena `microcred-api` dijalankan dengan 1 proses worker Uvicorn dan `pwd_context.verify()` dipanggil secara sinkron di dalam handler `async def`, proses tersebut memonopoli 1 core CPU (`~121%–146%` CPU pada `microcred-api`), sehingga peningkatan jumlah VU dari 1 menjadi 10 hanya memperpanjang antrean secara linier (`p50 ≈ VU × 256 ms`).

---

### E. Unggah File Besar 14 MB dan 17 MB (S5)

1. **File 14 MB bukan PDF (1, 3, 5 VU selama 20 detik -> `400` dari aplikasi Matkul):**
   - Karena ukuran 14 MB berada di bawah batas NGINX `location /api/matkul-recommender/` (`client_max_body_size 16m;`) dan subrequest `/_auth` memiliki `client_max_body_size 0;`, NGINX memverifikasi token terlebih dahulu lalu meneruskan body multipart 14 MB ke container `matkul`.
   - Aplikasi Next.js (`matkul`) membaca multipart form dan menolak file karena tipe MIME bukan `application/pdf` dengan status **`400`** (100% HTTP `400`, tanpa memanggil LLM).
   - Throughput mencapai `16,45 req/s` pada 1 VU (~230 MB/s), `25,65 req/s` pada 3 VU (~359 MB/s), dan `25,15 req/s` pada 5 VU (~352 MB/s), dengan `p50` naik dari `50,74 ms` (1 VU) ke `181,00 ms` (5 VU).
   - **Dampak memori:** Memori puncak container `superapp-matkul-1` naik secara signifikan saat mem-buffer multipart 14 MB di Node.js: dari baseline `~208 MiB` menjadi **`298,0 MiB` (1 VU)**, **`389,8 MiB` (3 VU)**, dan **`429,5 MiB` (5 VU)**, dengan CPU puncak mencapai **`285,17%`**. Sementara itu, memori `superapp-nginx-1` hanya naik tipis dari `11,2 MiB` ke **`20,8 MiB`** (karena NGINX mem-buffer ke disk sementara `/tmp`).
2. **File 17 MB pada 20 req/s selama 30 detik (-> `413` JSON dari NGINX):**
   - Seluruh **601 permintaan** pada tiap ulangan ditolak langsung oleh NGINX dengan status **`413`** dan `Content-Type: application/json` (`{"detail":"Ukuran file melebihi batas"}`) karena melampaui `client_max_body_size 16m`.
   - Latensi penolakan sangat cepat: **`p50 = 0,13 ms`**, **`p95 = 8,67 ms`**, **`p99 = 10,91 ms`**.
   - Container `superapp-nginx-1` hanya memakai memori puncak **`10,8 MiB`** (CPU `17,38%`), dan beban tersebut sama sekali tidak diteruskan ke aplikasi `matkul`.

---

### F. Rute Terproteksi Judul Recommender Tanpa LLM (S6 pada 50 dan 200 req/s)

- Rute `GET /api/judul-recommender/` melewati verifikasi JWT di NGINX + `auth-verifier` lalu diteruskan ke endpoint statis `GET /` pada `judul-api` (tanpa database dan tanpa LLM).
- Pada **50 req/s**: `p50 = 3,07 ms`, `p95 = 4,81 ms`, `p99 = 5,65 ms`, `error rate = 0%`, `dropped_iterations = 0`.
- Pada **200 req/s**: `p50 = 2,66 ms`, `p95 = 3,71 ms`, `p99 = 6,08 ms`, `error rate = 0%`, `dropped_iterations = 0`.
- Hasil ini menegaskan bahwa jalur autentikasi terpusat (`nginx` + `auth-verifier`) mampu menangani 200 req/s permintaan terautentikasi dengan latensi `p95 < 4 ms` apabila layanan upstream tidak terhambat oleh kueri database atau operasi sinkron berat.

---

## 6. Skenario yang Dilewati Beserta Alasannya

- **Skenario S7 (`s7-judul-llm.js` dan `s7-microcred-llm.js`):**
  - **Status:** Dilewati (tidak dijalankan). Skrip uji [`s7-judul-llm.js`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/s7-judul-llm.js) dan [`s7-microcred-llm.js`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/s7-microcred-llm.js) telah disediakan lengkap di dalam folder `gateway/tests/perf/` dan diintegrasikan ke [`run-perf.ps1`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/gateway/tests/perf/run-perf.ps1) di balik parameter `-IncludeLlm`.
  - **Alasan:**
    1. Sesuai aturan keras tugas, skenario yang memanggil layanan LLM berbayar (OpenAI pada Micro-cred dan Groq pada Judul) **wajib mati secara default** (`-IncludeLlm:$false`) dan tidak boleh diaktifkan sendiri tanpa instruksi eksplisit.
    2. Selain itu, berdasarkan pengujian E2E sebelumnya ([`docs/e2e-results.md`](file:///d:/File/Kuliah/Semester%206/Penelitian%20Tugas%20Akhir/SuperApp/superapp-gateway/docs/e2e-results.md)), akun OpenAI pada lingkungan ini sedang kehabisan kredit (`You have no credits remaining`), sehingga pemanggilan S7 pada Micro-cred akan langsung mengenai kondisi penghentian otomatis (`"no credits"`).

---

## 7. Keterbatasan Pengujian

1. **Satu Mesin untuk Klien dan Server:** Container generator beban (`grafana/k6`), pencatat `docker stats`, serta kesembilan container layanan (`superapp-*`) berjalan di atas laptop yang sama, sehingga saling berbagi CPU, memori, dan I/O disk.
2. **Berbagi CPU dan RAM pada Docker Desktop / WSL2:** Seluruh container berjalan di dalam VM WSL2 yang berbagi 4 core fisik (8 thread logis) Intel Core i5-1135G7 dan alokasi RAM ~3,74 GiB. Ketika `k6` membangkitkan beban tinggi (mis. 800 req/s) atau `matkul` memproses upload 14 MB paralel, proses `k6` sendiri ikut mengonsumsi CPU di VM yang sama.
3. **Bukan Konfigurasi Produksi:** Layanan Python (`microcred-api`, `auth-verifier`, `judul-api`) masing-masing berjalan dengan **1 worker Uvicorn** tanpa replika horizontal. Pada produksi, penggunaan multi-worker Gunicorn/Uvicorn akan meningkatkan kapasitas konkurensi CPU (terutama untuk operasi sinkron seperti `bcrypt` pada S4) secara proporsional.
4. **Jumlah Ulangan dan Durasi Terbatas:** Setiap skenario diuji sebanyak 3 ulangan dengan durasi pengukuran 20–30 detik per ulangan. Pengujian ini cukup untuk menangkap karakteristik latensi dan titik jenuh jangka pendek, namun belum menguji kebocoran memori jangka panjang (*soak testing* berjam-jam).
5. **Tanpa Rate Limiting:** Gateway maupun aplikasi belum menerapkan *rate limiting* per IP atau per akun, sehingga pada S3 (800 req/s tanpa token) dan S4 (login beruntun), seluruh permintaan diproses penuh oleh `auth-verifier` atau `microcred-api`.

---

## 8. Cara Menjalankan Ulang

```powershell
# Menjalankan seluruh skenario non-LLM (S1 sampai S6) dengan 3 ulangan:
powershell -NoProfile -File gateway\tests\perf\run-perf.ps1 -Repeats 3

# Menjalankan satu skenario tertentu saja (mis. S1):
powershell -NoProfile -File gateway\tests\perf\run-perf.ps1 -Repeats 3 -OnlyScenario S1
```

