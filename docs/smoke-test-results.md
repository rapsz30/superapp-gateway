# Laporan Hasil Smoke Test Autentikasi & Keamanan Gateway (`superapp-gateway`)

Dokumen ini mencatat hasil eksekusi pengujian otomatis [`gateway/auth/smoke-test.ps1`](../gateway/auth/smoke-test.ps1) terhadap **SuperApp Gateway** (`http://127.0.0.1:8080`). Pengujian memverifikasi penegakan autentikasi JWT terpusat (`auth_request` NGINX + `auth-verifier`), kontrol akses berbasis *role* (RBAC), normalisasi URI, batas ukuran unggahan (*upload limit*), kebijakan CORS, ketahanan terhadap manipulasi token/header, serta perilaku *fail-closed* saat layanan verifier berhenti.

---

## 1. Ringkasan Eksekusi

- **Skrip Uji**: [`gateway/auth/smoke-test.ps1`](../gateway/auth/smoke-test.ps1)
- **Target Gateway**: `http://127.0.0.1:8080`
- **Total Kasus Uji**: **38 kasus uji** (dalam 14 kelompok pengujian)
- **Hasil Akhir**: **38 PASS / 0 FAIL** (`exit code 0`)
- **Status Akhir Stack**: Seluruh 9 container berjalan normal dan `healthy`.

---

## 2. Tabel Rincian Hasil Per Kasus Uji

| No | Kelompok Uji | Kasus Uji | Endpoint & Metode | Ekspektasi | Hasil Aktual | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| 1 | **1. Publik tanpa token** | Healthcheck gateway | `GET /healthz` | `200` | `200` | **PASS** |
| 2 | **1. Publik tanpa token** | Healthcheck Micro-cred | `GET /api/micro-cred/health` | `200` | `200` | **PASS** |
| 3 | **1. Publik tanpa token** | Registrasi akun mahasiswa baru | `POST /api/micro-cred/auth/register` | `201` | `201` | **PASS** |
| 4 | **1. Publik tanpa token** | Login akun mahasiswa & ambil JWT | `POST /api/micro-cred/auth/login` | `200` + `access_token` | `200` | **PASS** |
| 5 | **2. Tanpa token -> 401 JSON** | Akses katalog tracks tanpa token | `GET /api/micro-cred/tracks` | `401` (`Token tidak ada atau tidak valid`) | `401 Token tidak ada atau tidak valid` | **PASS** |
| 6 | **2. Tanpa token -> 401 JSON** | Akses profil `/auth/me` tanpa token | `GET /api/micro-cred/auth/me` | `401` (`Token tidak ada atau tidak valid`) | `401 Token tidak ada atau tidak valid` | **PASS** |
| 7 | **2. Tanpa token -> 401 JSON** | Akses root Judul Recommender tanpa token | `GET /api/judul-recommender/` | `401` (`Token tidak ada atau tidak valid`) | `401 Token tidak ada atau tidak valid` | **PASS** |
| 8 | **2. Tanpa token -> 401 JSON** | Rekomendasi judul tanpa token | `POST /api/judul-recommender/get-recommendations` | `401` (`Token tidak ada atau tidak valid`) | `401 Token tidak ada atau tidak valid` | **PASS** |
| 9 | **2. Tanpa token -> 401 JSON** | Rekomendasi matkul tanpa token | `POST /api/matkul-recommender/rekomendasi` | `401` (`Token tidak ada atau tidak valid`) | `401 Token tidak ada atau tidak valid` | **PASS** |
| 10 | **3. Integritas Signature** | Token diubah 1 karakter terakhir | `GET /api/micro-cred/auth/me` | `401` | `401` | **PASS** |
| 11 | **4. Masa Berlaku Token** | Token kedaluwarsa (`exp = now - 60`) | `GET /api/micro-cred/auth/me` | `401` | `401` | **PASS** |
| 12 | **4b. Kunci Rahasia Asing** | Token ditandatangani dengan *secret* lain | `GET /api/micro-cred/auth/me` | `401` | `401` | **PASS** |
| 13 | **5. Token `student` sah** | Profil mahasiswa sendiri | `GET /api/micro-cred/auth/me` | `200` | `200` | **PASS** |
| 14 | **5. Token `student` sah** | Daftar tracks Micro-cred | `GET /api/micro-cred/tracks` | `200` | `200` | **PASS** |
| 15 | **5. Token `student` sah** | Rekomendasi Judul TA | `POST /api/judul-recommender/get-recommendations` | `200` (atau `500` dari upstream, lolos gateway) | `200` | **PASS** |
| 16 | **5. Token `student` sah** | Ekstraksi buku panduan Matkul (file non-PDF) | `POST /api/matkul-recommender/panduan/extract-upload` | `400` (validasi aplikasi Matkul) | `400` | **PASS** |
| 17 | **6. RBAC `student` ditolak** | Mahasiswa mencoba membuat track baru | `POST /api/micro-cred/tracks` | `403` (`Akses ditolak`) | `403 Akses ditolak` | **PASS** |
| 18 | **6b. Bypass Kebijakan Path** | Query string pada path terbatas | `POST /api/micro-cred/tracks?x=1` | `403` (`Akses ditolak`) | `403` | **PASS** |
| 19 | **6b. Bypass Kebijakan Path** | URL percent-encoding (`%74racks`) | `POST /api/micro-cred/%74racks` | `403` (`Akses ditolak`) | `403` | **PASS** |
| 20 | **6b. Bypass Kebijakan Path** | Double slash (`//tracks`) | `POST /api/micro-cred//tracks` | `403` (`Akses ditolak`) | `403` | **PASS** |
| 21 | **6b. Bypass Kebijakan Path** | Trailing slash (`/tracks/`) | `POST /api/micro-cred/tracks/` | `403` (`Akses ditolak`) | `403` | **PASS** |
| 22 | **7. RBAC `admin` diizinkan** | Admin mengirim `POST /tracks` (body `{}`) | `POST /api/micro-cred/tracks` | Lolos gateway (bukan `401`/`403`/`502`/`503`) | `422` (validasi skema FastAPI) | **PASS** |
| 23 | **8. Batas Ukuran Upload** | Upload file 14 MB pada rute Matkul (batas 16 MB) | `POST /api/matkul-recommender/panduan/extract-upload` | Lolos batas ukuran (`!= 413`, `< 500`) | `400` (bukan PDF valid) | **PASS** |
| 24 | **8. Batas Ukuran Upload** | Upload file 17 MB pada rute Matkul (> 16 MB) | `POST /api/matkul-recommender/panduan/extract-upload` | `413` (`Ukuran file melebihi batas`) | `413` | **PASS** |
| 25 | **9. Kebijakan CORS** | Preflight dari origin diizinkan (`http://127.0.0.1:5500`) | `OPTIONS /api/judul-recommender/get-recommendations` | `204` + header `Access-Control-Allow-Origin` cocok | `204` | **PASS** |
| 26 | **9. Kebijakan CORS** | Preflight dari origin asing (`http://evil.example`) | `OPTIONS /api/judul-recommender/get-recommendations` | `204` tanpa `Access-Control-Allow-Origin` | `204` | **PASS** |
| 27 | **9. Kebijakan CORS** | Respons galat `401` tetap menyertakan header CORS | `GET /api/judul-recommender/` | `401` + header `Access-Control-Allow-Origin` cocok | `401` | **PASS** |
| 28 | **10. Anti-Spoofing Header** | `student` mengirim `X-User-Roles: admin` palsu | `POST /api/micro-cred/tracks` | `403` (header klien ditimpa hasil verifier) | `403` | **PASS** |
| 29 | **10b. Token Berbahaya** | Algoritma `none` tanpa signature (`roles: ["admin"]`) | `GET /api/micro-cred/auth/me` | `401` | `401` | **PASS** |
| 30 | **10b. Token Berbahaya** | Algoritma `HS512` ditandatangani dengan *secret* asli | `GET /api/micro-cred/auth/me` | `401` (algoritma dikunci ke `HS256`) | `401` | **PASS** |
| 31 | **10b. Token Berbahaya** | Klaim `roles: ["superadmin"]` (role tidak dikenal) | `GET /api/micro-cred/auth/me` | `403` | `403` | **PASS** |
| 32 | **10b. Token Berbahaya** | Klaim `roles: []` (daftar role kosong) | `GET /api/micro-cred/auth/me` | `403` | `403` | **PASS** |
| 33 | **10b. Token Berbahaya** | Klaim `sub: ""` (subject kosong) | `GET /api/micro-cred/auth/me` | `401` | `401` | **PASS** |
| 34 | **10b. Token Berbahaya** | Klaim `email` berkarakter non-ASCII (`nändu-例@...`) | `GET /api/micro-cred/auth/me` | Bukan `401`/`503` (verifier tidak crash encoding Latin-1) | `404` (user uji tidak ada di DB Micro-cred) | **PASS** |
| 35 | **10c. Rute Publik Eksak** | Metode salah pada rute login publik | `GET /api/micro-cred/auth/login` | `405` (`Method not allowed`) | `405 Method not allowed` | **PASS** |
| 36 | **10c. Rute Publik Eksak** | Slash akhir pada rute register tanpa token | `POST /api/micro-cred/auth/register/` | `401` (tidak cocok `location =`, jatuh ke rute terproteksi) | `401` | **PASS** |
| 37 | **11. Verifier Mati (*Fail-Closed*)** | Akses rute terproteksi saat `auth-verifier` mati | `GET /api/judul-recommender/` | `503` (`Layanan autentikasi tidak tersedia`) | `503 Layanan autentikasi tidak tersedia` | **PASS** |
| 38 | **11. Verifier Mati (*Fail-Closed*)** | Akses health publik saat `auth-verifier` mati & pemulihan | `GET /api/micro-cred/health` lalu `GET /api/micro-cred/auth/me` | `200` saat mati, dan `200` setelah `start auth-verifier` + `restart nginx` | `200` & `200` | **PASS** |

---

## 3. Output Konsol Eksekusi (`smoke-test.ps1`)

```text
== 1. Publik tanpa token
PASS  GET /healthz  (200)
PASS  GET /api/micro-cred/health  (200)
PASS  POST register  (201)
PASS  POST login  (200)
== 2. Tanpa token -> 401 JSON dari gateway
PASS  GET /api/micro-cred/tracks tanpa token  (401 Token tidak ada atau tidak valid)
PASS  GET /api/micro-cred/auth/me tanpa token  (401 Token tidak ada atau tidak valid)
PASS  GET /api/judul-recommender/ tanpa token  (401 Token tidak ada atau tidak valid)
PASS  POST /api/judul-recommender/get-recommendations tanpa token  (401 Token tidak ada atau tidak valid)
PASS  POST /api/matkul-recommender/rekomendasi tanpa token  (401 Token tidak ada atau tidak valid)
== 3. Token diubah satu karakter -> 401
PASS  token diubah  (401)
== 4. Token kedaluwarsa -> 401
PASS  token kedaluwarsa  (401)
== 4b. Token ditandatangani dengan secret lain -> 401
PASS  token secret lain  (401)
== 5. Token student sah
PASS  GET /auth/me  (200)
PASS  GET /tracks  (200)
PASS  POST get-recommendations  (200)
PASS  POST extract-upload bukan PDF  (400)
== 6. Student menulis tracks -> 403 dari gateway
PASS  POST /tracks (student)  (403 Akses ditolak)
== 6b. Percobaan melewati kebijakan (student)
PASS  POST /api/micro-cred/tracks?x=1  (403)
PASS  POST /api/micro-cred/%74racks  (403)
PASS  POST /api/micro-cred//tracks  (403)
PASS  POST /api/micro-cred/tracks/  (403)
== 7. Admin menulis tracks -> bukan 401/403 dari gateway
PASS  POST /tracks (admin)  (422)
== 8. Batas upload dengan token student
PASS  upload 14 MB  (400)
PASS  upload 17 MB  (413)
== 9. CORS
PASS  preflight origin diizinkan  (204)
PASS  preflight origin asing  (204)
PASS  401 memuat header CORS  (401)
== 10. Pemalsuan header X-User-*
PASS  student + header admin palsu tetap 403  (403)
== 10b. Token berbahaya dibuat di container
PASS  token alg none  (401)
PASS  token HS512 secret asli  (401)
PASS  roles ["superadmin"]  (403)
PASS  roles []  (403)
PASS  sub ""  (401)
PASS  email non-ASCII  (404)
== 10c. Rute publik eksak dengan method salah dan slash akhir
PASS  GET /auth/login -> 405 JSON  (405 Method not allowed)
PASS  POST /auth/register/ tanpa token -> 401  (401)
== 11. Verifier mati (fail closed)
PASS  rute terproteksi -> 503  (503 Layanan autentikasi tidak tersedia)
PASS  health publik tetap 200  (200)
PASS  pulih setelah start verifier + restart nginx  (200)
auth-verifier Up 29 seconds (healthy)
db Up 4 minutes (healthy)
judul-api Up 4 minutes (healthy)
matkul Up 4 minutes (healthy)
microcred-api Up 4 minutes (healthy)
microcred-worker Up 4 minutes
nginx Up 12 seconds (healthy)
pocketbase Up 4 minutes (healthy)
redis Up 4 minutes (healthy)
== Ringkasan: 0 FAIL
```

