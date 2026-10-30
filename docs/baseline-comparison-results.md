# Laporan Pengujian Baseline Akses Langsung ("Standalone") vs Gateway dan Evaluasi Fase B

Tanggal penyusunan: **2026-10-30**  
Orkestrator: [`gateway/tests/baseline/run-baseline.ps1`](../gateway/tests/baseline/run-baseline.ps1) (`FASE_DIJALANKAN: A`, `-Repeats 3`)  
Skrip beban k6: [`gateway/tests/baseline/baseline-k6.js`](../gateway/tests/baseline/baseline-k6.js)  
Konfigurasi NGINX tanpa autentikasi: [`gateway/tests/baseline/nginx-noauth.conf`](../gateway/tests/baseline/nginx-noauth.conf)  
Berkas tabel hasil terformat (`-Report`): [`docs/baseline-comparison-tables.md`](./baseline-comparison-tables.md)  

> [!IMPORTANT]
> **Status Eksekusi & Perkiraan Durasi Fase A Penuh:**  
> - Pengujian **Fase A penuh** mencakup **99 run** (`11 kondisi × 3 jalur × 3 ulangan`). Setiap run terdiri atas 10 detik *warm-up*, 30 detik fase ukur, pemantauan kondisi tenang CPU (`< 5%` pada 2 sampel beruntun, maksimal 60 detik), serta jeda tetap 15 detik, sehingga membutuhkan **perkiraan waktu total 2 sampai 3,5 jam**.  
> - Sesuai instruksi, Fase A penuh dan Fase B belum dijalankan pada tahap ini, sehingga seluruh sel metrik yang belum diukur ditulis **`tidak diukur`** (tidak diestimasi).  
> - Setelah Fase A selesai dijalankan (`powershell -File gateway/tests/baseline/run-baseline.ps1 -Phase A -Repeats 3`), jalankan perintah berikut untuk menghasilkan tabel lengkap dari `gateway/tests/baseline/out/phase-a-summary.json` ke [`docs/baseline-comparison-tables.md`](./baseline-comparison-tables.md) tanpa menimpa dokumen ini:
>   ```powershell
>   powershell -File gateway/tests/baseline/run-baseline.ps1 -Report
>   ```

---

## 1. Tujuan dan Definisi Operasional

### 1.1. Tujuan Eksperimen
Menutup dua celah bukti empiris untuk naskah *"From Standalone to Microservices"*:
1. **Bukti Jenis 1 — Baseline Akses Langsung (*Access Path & Central Auth Overhead*)**: Mengukur dan memisahkan biaya jalur *reverse proxy* NGINX (`noauth` minus `direct`) serta biaya autentikasi terpusat `auth_request` + `auth-verifier` (`gateway` minus `noauth`) pada **ketiga layanan** (`Micro-cred`, `Judul`, dan `Matkul`) di bawah kondisi jaringan dan beban yang setara.
2. **Bukti Jenis 2 — Evaluasi Fungsional Alur Rekomendasi (*Functional End-to-End Verification*)**: Membuktikan bahwa ketiga layanan (khususnya alur penuh rekomendasi `Matkul` dengan dokumen PDF KHS serta buku panduan akademik, dan uji ulang `Micro-cred`) benar-benar berfungsi secara teknis setelah integrasi melalui gateway (dieksekusi khusus pada **Fase B**).

> [!WARNING]
> **Pemisahan Tegas Dua Jenis Bukti:**  
> - **Fase A** hanya mengukur perbedaan latensi/throughput jalur akses tanpa memanggil LLM dan **tidak boleh dinyatakan menutup evaluasi fungsional rekomendasi Matkul**.  
> - Evaluasi fungsional rekomendasi Matkul baru dinyatakan selesai apabila **Fase B** (`-Phase B`) telah dijalankan dengan berkas `fixtures/khs-sample.pdf` dan `fixtures/panduan-sample.pdf` serta menghasilkan data aktual yang memenuhi kriteria keberhasilan teknis.

### 1.2. Definisi Operasional "Standalone" dalam Paper
Dalam dokumen ini dan naskah paper, istilah **"standalone" (`direct`)** didefinisikan secara ketat sebagai:
> **Layanan container yang sama yang diakses secara langsung di dalam jaringan Docker yang sama (`superapp_default`), tanpa melalui reverse proxy NGINX dan tanpa autentikasi terpusat (`auth-verifier`).**

Konfigurasi ini **BUKAN** *deployment non-container* asli yang berdiri sendiri di mesin/lingkungan terpisah. Oleh karena itu, hasil perbandingan baseline ini **hanya mengukur perbedaan biaya jalur akses dan autentikasi terpusat**, bukan keunggulan arsitektur *microservices* dibandingkan *monolith/standalone* secara keseluruhan.

---

## 2. Audit Kode Endpoint Sebelum Eksperimen (Ketentuan Tambahan 1)

Sebelum skrip Fase A disusun, seluruh kode sumber endpoint yang diuji telah dibaca secara statis untuk memeriksa apakah ada pemanggilan LLM atau penulisan data persisten:

| Kode Kondisi | Layanan & Endpoint | Berkas Kode Sumber | Hasil Pembacaan Kode Statis |
|---|---|---|---|
| **M1** | Micro-cred `GET /tracks` | [`services/microcred/src/api/routes/tracks.py`](../services/microcred/src/api/routes/tracks.py#L27-L52) | Hanya menjalankan 2 query `SELECT` *read-only* (`RoleCatalog` dan `func.count(QuestionTemplate.id)`). Berdasarkan pembacaan kode, tidak memanggil LLM dan tidak menulis ke DB. |
| **M2** | Micro-cred `GET /auth/me` | [`services/microcred/src/api/routes/auth.py`](../services/microcred/src/api/routes/auth.py#L111-L133) | Memverifikasi JWT melalui `get_current_user` dan menjalankan 1 query `SELECT` *read-only* (`get_user_by_id`). Berdasarkan pembacaan kode, tidak memanggil LLM dan tidak menulis ke DB. |
| **J1** | Judul `GET /` | [`services/judul/main.py`](../services/judul/main.py#L31-L37) | Mengembalikan JSON statis dari memori (`{"status": "Online", ...}`). Berdasarkan pembacaan kode, tidak memanggil Groq/LLM dan tidak menulis data apa pun. |
| **K1** | Matkul `POST /api/panduan/extract-upload` (berkas teks non-PDF) | [`services/matkul/app/api/panduan/extract-upload/route.ts`](../services/matkul/app/api/panduan/extract-upload/route.ts#L8-L45) | Memeriksa `if (file.type !== "application/pdf")` pada baris 17 dan langsung mengembalikan HTTP `400` (`{"error": "File harus berformat PDF."}`) tanpa memanggil `pdf-parse` maupun OpenAI. |
| **K2** | Matkul `POST /api/panduan/extract-upload` (PDF valid minimal) | [`services/matkul/app/api/panduan/extract-upload/route.ts`](../services/matkul/app/api/panduan/extract-upload/route.ts#L25-L41) & [`panduan-extract.ts`](../services/matkul/src/lib/panduan-extract.ts#L12-L21) | Mengekstrak teks PDF di memori menggunakan `pdf-parse/lib/pdf-parse.js` lalu mengembalikan HTTP `200` (`{ ok: true, text, extracted_chars }`). **Berdasarkan hasil pembacaan kode (bukan pengukuran runtime), route ini tidak memanggil SDK PocketBase dan tidak memanggil OpenAI/LLM.** |

### Audit Kode Endpoint Fase B & Verifikasi Manual PocketBase
Berdasarkan pembacaan kode sumber statis pada layanan Matkul:
- [`services/matkul/app/api/khs/upload/route.ts`](../services/matkul/app/api/khs/upload/route.ts#L83-L143): Menerima `multipart/form-data` field `file` (`application/pdf`), mengekstrak teks via `pdf-parse`, lalu memanggil `extractKhsFromText(text)` ([`src/lib/openai.ts`](../services/matkul/src/lib/openai.ts#L40-L123)) dan mengembalikan `{ ok: true, preview }`.
- [`services/matkul/app/api/rekomendasi/route.ts`](../services/matkul/app/api/rekomendasi/route.ts#L75-L244): Menerima JSON `{ khs, panduan_text }`, menghitung `semester_target` melalui `calcSemesterTarget(khs, evaluatedRows)`, memanggil OpenAI `chat.completions.create`, dan mengembalikan `{ semester_target, ringkasan, evaluasi_nilai, rekomendasi_semester_depan }`.

> [!NOTE]
> Pernyataan bahwa route API `/api/khs/upload`, `/api/panduan/extract-upload`, dan `/api/rekomendasi` tidak menulis record ke PocketBase merupakan **kesimpulan hasil pembacaan kode sumber statis (`route.ts`), BUKAN hasil pengukuran oleh skrip**. Di dalam `phase-b-summary.json`, status ini dicatat sebagai `"tidak diukur oleh skrip, diverifikasi manual"`.

#### Verifikasi Manual PocketBase (Diisi oleh Peneliti Saat Menjalankan Fase B)
Peneliti dapat memeriksa dashboard admin atau koleksi PocketBase sebelum dan sesudah menjalankan Fase B (`-Phase B`) dan mengisi tabel berikut secara manual:

| Nama Koleksi PocketBase | Jumlah Record Sebelum Fase B | Jumlah Record Sesudah Fase B | Selisih ($\Delta$) | Catatan Verifikasi Manual |
|---|---|---|---|---|
| `users` | tidak diukur | tidak diukur | tidak diukur | Diisi manual oleh peneliti sebelum & sesudah Fase B |
| `khs` / `riwayat_rekomendasi` (bila ada) | tidak diukur | tidak diukur | tidak diukur | Diisi manual oleh peneliti sebelum & sesudah Fase B |
| Koleksi lain (sebutkan bila ada) | tidak diukur | tidak diukur | tidak diukur | Diisi manual oleh peneliti sebelum & sesudah Fase B |

---

## 3. Lingkungan dan Metode Pengujian

### 3.1. Spesifikasi Lingkungan Host & Docker
Berdasarkan pemeriksaan sistem pada mesin pengujian:

| Komponen | Spesifikasi |
|---|---|
| Sistem Operasi Host | Microsoft Windows 11 Home Single Language, Versi `10.0.26200` (Build `26200`), x64 |
| Prosesor (CPU) | 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz (4 core fisik, 8 prosesor logis) |
| Memori Fisik Host | 7.883 MB (~7,70 GiB) |
| Docker Engine & WSL2 | Docker Desktop `29.8.0` (build `88096ef`), Linux `5.15.153.1-microsoft-standard-WSL2` (8 vCPU, RAM ~3.831 MiB) |
| Generator Beban | `grafana/k6:latest` di jaringan `superapp_default` |

### 3.2. Tiga Jalur Akses per Layanan (A1)
Seluruh permintaan dikirim dari container `grafana/k6` di dalam jaringan Docker `superapp_default`:
1. **Jalur 1 — Langsung (`direct` / "standalone")**:
   - Micro-cred: `http://microcred-api:8000/tracks` (`M1`), `http://microcred-api:8000/auth/me` (`M2`)
   - Judul: `http://judul-api:8001/` (`J1`)
   - Matkul: `http://matkul:3000/api/panduan/extract-upload` (`K1`, `K2`)
2. **Jalur 2 — NGINX Tanpa Autentikasi (`noauth`)**:
   - Menggunakan container sementara `superapp-nginx-noauth` (`nginx:1.27-alpine`, di jaringan `superapp_default`, tanpa port host) yang memuat [`gateway/tests/baseline/nginx-noauth.conf`](../gateway/tests/baseline/nginx-noauth.conf).
   - Fungsi `Ensure-NginxNoAuthConfig` di [`run-baseline.ps1`](../gateway/tests/baseline/run-baseline.ps1) memvalidasi keberadaan baris `auth_request /_auth;` menggunakan regex toleran spasi dan melempar galat apabila hasil penggantian identik dengan berkas sumber.
   - Sebelum pengujian dimulai, probe ke `http://superapp-nginx-noauth/api/judul-recommender/` tanpa token dibungkus `try/catch` dan wajib mengembalikan HTTP `200` dengan penambahan baris log `auth-verifier` sama dengan `0`. Selain itu, setelah setiap run jalur `noauth`, apabila `verifier_log_delta > 0`, skrip menandai `noauth_verifier_hits = true` di ringkasan JSON dan mengeluarkan peringatan.
   - Diff eksak antara [`gateway/nginx/nginx.conf`](../gateway/nginx/nginx.conf) dan [`gateway/tests/baseline/nginx-noauth.conf`](../gateway/tests/baseline/nginx-noauth.conf):
     ```diff
     diff --git a/gateway/nginx/nginx.conf b/gateway/tests/baseline/nginx-noauth.conf
     index 1c8175f..0aa510c 100644
     --- a/gateway/nginx/nginx.conf
     +++ b/gateway/tests/baseline/nginx-noauth.conf
     @@ -62,7 +62,7 @@ http {
              client_max_body_size 1m;
      
              # --- Autentikasi terpusat: default tolak, rute publik memakai "auth_request off" ---
     -        auth_request /_auth;
     +        auth_request off;
              auth_request_set $auth_user_id    $upstream_http_x_user_id;
              auth_request_set $auth_user_roles $upstream_http_x_user_roles;
              auth_request_set $auth_user_email $upstream_http_x_user_email;
     ```
3. **Jalur 3 — Gateway Penuh (`gateway`)**:
   - Rute melalui container `http://nginx` dengan `auth_request /_auth` aktif (memverifikasi JWT ke `auth-verifier:8100/verify`).

### 3.3. Aturan Kesetaraan, Rotasi Jalur, Jeda Tenang, dan Interval `docker stats` (A2 & A3)
- **Kesetaraan Header & Payload:** Satu akun uji (`uji-base-<timestamp>@example.com`) didaftarkan di awal Fase A. Header `Authorization: Bearer <token>` yang **sama persis** dikirim di ketiga jalur (`direct`, `noauth`, `gateway`) dan semua layanan agar ukuran header HTTP identik. Pada rute publik (`GET /tracks`) atau layanan tanpa autentikasi internal (`Judul`, `Matkul`, serta NGINX `noauth`), header tersebut diabaikan oleh komponen penerima.
- **Konfigurasi Executor & Fase Ukur:** Menggunakan `constant-arrival-rate` dengan **warm-up 10 detik** (`tags: { phase: 'warmup' }`, tidak dihitung) diikuti **fase ukur 30 detik** (`tags: { phase: 'main' }`). Hanya metrik fase ukur yang diekspor ke `main_*`.
- **Rotasi Urutan Jalur per Ulangan:** Untuk menghilangkan bias urutan pemanasan cache/koneksi, urutan ketiga jalur dirotasi pada setiap ulangan:
  - Ulangan 1: `direct` $\rightarrow$ `noauth` $\rightarrow$ `gateway`
  - Ulangan 2: `noauth` $\rightarrow$ `gateway` $\rightarrow$ `direct`
  - Ulangan 3: `gateway` $\rightarrow$ `direct` $\rightarrow$ `noauth`
- **Jeda Tenang (*Cooldown*):** Sebelum setiap eksekusi dimulai, orkestrator memantau `docker stats --no-stream` hingga total CPU seluruh container berada **di bawah 5% pada dua sampel beruntun** (batas tunggu maksimal 60 detik; ditandai `"tidak tenang"` bila melampaui 60 detik), lalu menunggu **15 detik** tambahan.
- **Pencatatan Resource Container & Interval Sampel Aktual:** Selama eksekusi berjalan, [`collect-stats.ps1`](../gateway/tests/baseline/collect-stats.ps1) memanggil `docker stats --no-stream` secara berurutan di dalam loop tanpa `Start-Sleep` tambahan (karena satu panggilan `docker stats --no-stream` ke daemon Docker sendiri membutuhkan waktu sekitar 1–2 detik untuk mengumpulkan sampel seluruh container). Interval sampel median yang sebenarnya (`sample_interval_median_sec`) dihitung langsung dari selisih *timestamp* milidetik berurutan di berkas CSV pada jendela fase ukur 30 detik, lalu disimpan ke dalam `out/phase-a-summary.json` bersama nilai **median CPU (%) dan median memori (MiB)** per container (bukan puncak).

---

## 4. Hasil Fase A per Layanan dan Endpoint

> [!NOTE]
> Karena Fase A penuh (99 run, estimasi durasi 2–3,5 jam) belum dijalankan pada tahap ini, seluruh sel metrik di bawah ditulis **`tidak diukur`**. Setelah Fase A dijalankan, jalankan `powershell -File gateway/tests/baseline/run-baseline.ps1 -Report` untuk menghasilkan tabel lengkap di [`docs/baseline-comparison-tables.md`](./baseline-comparison-tables.md).

### 4.1. Tabel Perbandingan Tiga Jalur (`direct`, `noauth`, `gateway`)

> [!NOTE]
> **K2 bersifat opsional.** K2 (PDF valid) hanya dijalankan bila prasyarat terpenuhi: hasil pembacaan kode menunjukkan route tidak memanggil LLM maupun PocketBase, dan verifikasi satu request langsung ke `matkul:3000` mengembalikan HTTP `200` dengan `extracted_chars` > 0. Bila prasyarat tidak terpenuhi, K2 tidak dijalankan dan ditulis `tidak diukur`, **bukan** dianggap gagal.
>
> Pembacaan kode saja tidak menggantikan verifikasi runtime tersebut. Metadata eksperimen (waktu mulai, waktu selesai, ulangan diminta dan diselesaikan, status K2) dicatat skrip di `phase-a-summary.json` dan ditampilkan oleh `-Report`; bila tidak tersedia ditulis `tidak diukur`.

| Kondisi | Layanan & Endpoint | Laju Target | Jalur | p50 Median ( Rentang Min–Maks ) (ms) | p95 Median ( Rentang Min–Maks ) (ms) | p99 Median (ms) | Avg Median (ms) | Throughput (req/s) | Kegagalan (%) | Dropped Iterations | Status Pengukuran |
|---|---|---:|---|---|---|---|---|---|---|---|---|
| **M1-20** | Micro-cred `GET /tracks` | 20 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **M1-50** | Micro-cred `GET /tracks` | 50 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **M1-100** | Micro-cred `GET /tracks` | 100 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **M2-20** | Micro-cred `GET /auth/me` | 20 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **M2-50** | Micro-cred `GET /auth/me` | 50 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **J1-50** | Judul `GET /` | 50 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **J1-200** | Judul `GET /` | 200 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **K1-20** | Matkul `POST /api/panduan/extract-upload` (non-PDF $\rightarrow$ `400`) | 20 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **K1-50** | Matkul `POST /api/panduan/extract-upload` (non-PDF $\rightarrow$ `400`) | 50 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **K2-5** | Matkul `POST /api/panduan/extract-upload` (PDF valid $\rightarrow$ `200`) | 5 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |
| **K2-10** | Matkul `POST /api/panduan/extract-upload` (PDF valid $\rightarrow$ `200`) | 10 req/s | `direct` / `noauth` / `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | Belum dijalankan (lihat `-Report` setelah Fase A selesai) |

### 4.2. Tabel Dekomposisi Selisih Biaya (`Proxy`, `Autentikasi`, `Total`)

Rumus dekomposisi:
- $\Delta_{\text{proxy}} = \text{noauth} - \text{direct}$ (biaya penerusan *reverse proxy* NGINX tanpa subrequest `auth-verifier`)
- $\Delta_{\text{auth}} = \text{gateway} - \text{noauth}$ (biaya subrequest `auth_request /_auth` ke `auth-verifier`)
- $\Delta_{\text{total}} = \text{gateway} - \text{direct}$ (biaya total jalur gateway penuh terhadap akses langsung)
- **Aturan Tafsir:** Apabila rentang $[\text{min}, \text{maks}]$ dari `p50` antara dua jalur saling tumpang tindih, maka perbedaannya wajib ditafsirkan sebagai **"tidak dapat dibedakan pada pengukuran ini"**.
- **Fokus analisis:** p50 dan p95 adalah metrik utama untuk membandingkan overhead; p99 dan rata-rata disajikan pada tabel tiga jalur (Bagian 4.1) sebagai pelengkap.
- **Makna rentang:** rentang dihitung dari hasil **pengulangan** (selisih per nomor ulangan), bukan rentang variasi setiap request.

| Kondisi | $\Delta_{\text{proxy}}$ p50 (Rentang) | $\Delta_{\text{auth}}$ p50 (Rentang) | $\Delta_{\text{total}}$ p50 (Rentang) | $\Delta_{\text{proxy}}$ p95 (Rentang) | $\Delta_{\text{auth}}$ p95 (Rentang) | $\Delta_{\text{total}}$ p95 (Rentang) | Tafsir Berdasarkan Rentang p50 |
|---|---|---|---|---|---|---|---|
| **M1-20**, **M1-50**, **M1-100** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20**, **M2-50** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50**, **J1-200** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20**, **K1-50** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5**, **K2-10** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

### 4.3. Median CPU (%) dan Memori (MiB) Container pada Fase Ukur
- **Status:** `tidak diukur`. Setelah Fase A selesai, `-Report` menghasilkan dua tabel terpisah: median CPU (%) dan median memori (MiB) per container (Bagian 3.1 dan 3.2 pada [`docs/baseline-comparison-tables.md`](./baseline-comparison-tables.md)).

---

## 5. Tabel Siap Tempel untuk Paper (Perluasan Tabel 3)

Tabel di bawah memperluas struktur Tabel 3 pada naskah paper dengan memisahkan jalur akses (`Direct / Standalone`, `NGINX No-Auth`, `Full Gateway`) pada ketiga layanan. Untuk menghasilkan tabel terisi dari `out/phase-a-summary.json`, jalankan `powershell -File gateway/tests/baseline/run-baseline.ps1 -Report` yang akan menulis hasilnya ke [`docs/baseline-comparison-tables.md`](./baseline-comparison-tables.md):

| Layanan & Endpoint | Laju Target (req/s) | Jalur Akses | p50 (ms) [Min–Maks] | p95 (ms) [Min–Maks] | p99 (ms) | Rata-rata (ms) | Throughput (req/s) | Kegagalan (%) |
|---|---:|---|---|---|---|---|---|---|
| **Micro-cred** `GET /tracks` | 20 | Direct (`microcred-api:8000`) | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Micro-cred** `GET /tracks` | 20 | NGINX No-Auth (`auth_request off`) | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Micro-cred** `GET /tracks` | 20 | Full Gateway (`nginx` + `auth-verifier`) | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Micro-cred** `GET /tracks` | 50 | Direct / No-Auth / Full Gateway | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Micro-cred** `GET /tracks` | 100 | Direct / No-Auth / Full Gateway | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Micro-cred** `GET /auth/me` | 20, 50 | Direct / No-Auth / Full Gateway | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Judul** `GET /` | 50, 200 | Direct / No-Auth / Full Gateway | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Matkul** `POST /api/panduan/extract-upload` (`400` non-PDF) | 20, 50 | Direct / No-Auth / Full Gateway | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **Matkul** `POST /api/panduan/extract-upload` (`200` PDF valid) | 5, 10 | Direct / No-Auth / Full Gateway | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

---

## 6. Status Fase B (Evaluasi Alur Rekomendasi & Pasangan LLM)

- **Status:** **`tidak diukur`** (Fase B tidak dijalankan pada tugas ini).
- **Kesiapan Skrip Fase B (`-Phase B`):** Seluruh logika **B0, B1, B2, B3, dan B4** telah diimplementasikan di dalam [`gateway/tests/baseline/run-baseline.ps1`](../gateway/tests/baseline/run-baseline.ps1) (`Invoke-PhaseB`):
  - **B4** menjalankan **total 6 siklus** (1 siklus probe awal untuk memeriksa ketiadaan error kuota diikuti 5 siklus utama) menggunakan [`gateway/tests/e2e-flow.ps1`](../gateway/tests/e2e-flow.ps1), lalu menghitung jumlah event `essay_scoring_failed`, `essay_scoring_fallback_used`, `rag_no_matches`, `rag_fallback_activated`, dan `gpt_rate_limited` dari `docker compose logs --since` dan menyimpannya ke `out/phase-b-summary.json`.
- **Implikasi bagi Klaim Paper:** Sesuai Ketentuan Tambahan 3, **evaluasi fungsional rekomendasi Matkul belum dinyatakan selesai** sampai Fase B dijalankan dengan berkas `fixtures/khs-sample.pdf` dan `fixtures/panduan-sample.pdf` serta kredit API OpenAI/Groq aktif.

---

## 7. Interpretasi Netral dan Keterbatasan Metodologis

1. **Batas Definisi "Standalone":** Baseline akses langsung (`direct`) mengukur kontainer backend yang sama di dalam jaringan bridge Docker `superapp_default`, bukan aplikasi *standalone* non-container pada mesin terpisah. Dengan demikian, selisih waktu respons semata-mata merepresentasikan biaya *hop* proxy NGINX dan subrequest verifikasi JWT terpusat, **bukan** perbandingan efisiensi arsitektur *microservices* vs *monolith* secara umum.
2. **Satu Mesin Fisik (*Single-Host Contention*):** Generator beban (`grafana/k6`), reverse proxy (`nginx` / `superapp-nginx-noauth`), layanan autentikasi (`auth-verifier`), dan ketiga backend (`microcred-api`, `judul-api`, `matkul`) berbagi 8 vCPU WSL2 yang sama di satu laptop. Pada laju tinggi, kontensi penjadwalan CPU host dapat memperlebar rentang variansi antar-ulangan.
3. **Jumlah Ulangan Terbatas (3 Ulangan):** Dengan 3 ulangan per kondisi, rentang $[\text{min}, \text{maks}]$ pada metrik sub-milidetik atau beberapa milidetik mudah saling tumpang tindih akibat *jitter* OS/WSL2. Sesuai aturan tafsir, setiap kondisi yang rentang `p50`-nya saling tumpang tindih tidak boleh diklaim mengalami percepatan maupun perlambatan.
4. **Variansi Eksternal LLM pada Fase B:** Waktu respons pada endpoint yang memanggil OpenAI (`Matkul` dan `Micro-cred`) serta Groq (`Judul`) didominasi oleh latensi inferensi jaringan eksternal (orde detik), sehingga selisih antar-pasangan pada B2 dan B3 mencerminkan fluktuasi layanan cloud LLM, bukan overhead gateway (yang berada pada orde milidetik).
5. **Tidak Ada Pembanding Keandalan (*Reliability*) yang Setara:** Pengujian *fault injection* pada arsitektur terintegrasi membuktikan sifat **isolasi kegagalan (*fault isolation*)** dan perilaku *fail-closed* saat komponen terganggu, tetapi karena tidak ada pengujian *fault injection* pembanding pada deployment *standalone* independen, hasil tersebut **tidak boleh diklaim sebagai peningkatan keandalan (*higher reliability*) secara keseluruhan**.

---

## 8. Daftar Item yang Tidak Diukur Beserta Alasannya

| Item / Kondisi | Status | Alasan Eksplisit |
|---|---|---|
| **Fase A Penuh (`M1`, `M2`, `J1`, `K1`, `K2` — 99 run, 2–3,5 jam)** | `tidak diukur` | Instruksi tugas melarang menjalankan Fase A penuh pada tahap review skrip ini. |
| **Fase B (`B0`–`B4`: Alur penuh Matkul, pasangan LLM Matkul & Judul, uji ulang 6 siklus Micro-cred)** | `tidak diukur` | Instruksi tugas melarang menjalankan Fase B pada tahap ini dan membutuhkan berkas `fixtures/khs-sample.pdf` serta `fixtures/panduan-sample.pdf`. |
| **Jumlah Record PocketBase Sebelum & Sesudah Fase B** | `tidak diukur` | Tidak diukur oleh skrip (`pocketbase_records_note = "tidak diukur oleh skrip, diverifikasi manual"`); disediakan tabel verifikasi manual pada Bagian 2. |
| **Kualitas Substantif Isi Rekomendasi Akademik (Matkul, Judul, Micro-cred)** | `tidak diukur` | Di luar cakupan pengujian teknis sistem; evaluasi dibatasi secara eksplisit pada validitas skema JSON, kelengkapan atribut wajib (`kode`, `nama`, `semester_target`, `ringkasan`, `evaluasi_nilai`, `rekomendasi_semester_depan`), dan kode status HTTP. |
