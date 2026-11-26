# Audit sebelum deploy ke VPS (26 Nov 2026)

Cakupan: repo `superapp-gateway` pada branch `feat/hackathon-superapp-gateway` (termasuk perubahan yang belum di-commit), layanan yang berjalan di laptop, dan port instalasi AlurKerja lokal. Tidak ada kode yang diubah oleh audit ini.

## Kesimpulan

**Fungsi utama berjalan di laptop** (rencana studi, judul tugas akhir, analytics, akun dan peran) dan semua tes otomatis lolos. **Belum siap diunggah ke VPS**: ada 7 penghalang deploy dan beberapa celah keamanan.

## Yang lolos

| Pemeriksaan | Hasil |
|---|---|
| Tes identity | 162 lolos |
| Tes unit micro-credential (basis data tiruan) | 141 lolos |
| Tes matkul / connector / frontend / auth-verifier | 27 / 9 / 7 / 11 lolos |
| Cek tipe frontend, matkul, connector | tanpa galat |
| Build produksi frontend | berhasil (catatan: `ignoreBuildErrors: true`) |
| `docker compose config` mode gateway, `nginx -t` pada kontainer berjalan | sah |
| 13 layanan compose | menyala, yang punya healthcheck sehat |
| Halaman web utama (12 rute) | HTTP 200 (isi halaman tidak diperiksa satu per satu) |
| Tiga dashboard AlurKerja lewat identity | terbaca (7, 8, 5 kartu) |
| AI brainstorm judul (satu panggilan asli) | membalas |
| Permintaan tanpa token dan token palsu | 401; rute internal 404 |
| Mahasiswa mengakses audit, analytics, rekap tema, pembimbing TA, ubah struktur | 403 |
| Daftar pengajuan mahasiswa | hanya milik sendiri |
| Sandi salah berulang (akun sama) | ditahan (429) setelah 5 kali |
| Rahasia identity, matkul, judul, connector di berkas repo dan riwayat git | tidak ditemukan |

## Penghalang deploy (wajib)

1. **Perubahan belum di-commit.** 61 berkas diubah dan 41 berkas atau folder baru. VPS yang mengambil dari git tidak akan mendapat fitur-fitur ini.
2. **Frontend tidak ada di `docker-compose.yml`.** Tidak ada Dockerfile maupun layanan web; di laptop dijalankan dengan `next dev`. `API_BASE_URL` dipakai saat build.
3. **Tidak ada pintu masuk publik dan HTTPS.** NGINX hanya mendengar di `127.0.0.1:8080` tanpa TLS. Perlu reverse proxy dengan domain dan sertifikat di depan frontend.
4. **Konfigurasi terikat laptop.** `alurkerja.local` (`extra_hosts`, `ALURKERJA_URL`, `ALURKERJA_BASE_URL`) dan mount `alurkerja-connector/certs/rootCA.pem` (mkcert). Di VPS ganti alamatnya, hapus CA lokal bila memakai sertifikat asli. Berkas CA yang tidak ada akan dibuat Docker sebagai folder dan membuat koneksi gagal.
5. **AlurKerja di VPS harus disiapkan ulang.** Yang tidak ada di repo: deploy Live kedua BPMN, form tugas di Studio, pertanyaan SQL dan tiga dashboard (id-nya diisi di `.env`), Auth Token, akun layanan, akun dosen, id tenant Live. Lisensi belum aktif (`LICENSE_NOT_ACTIVATED`). Perbaikan layanan tenant ada di luar repo (`docker-compose.superapp-fix.yml`, lihat [15](identity/15-sinkron-akun-alurkerja.md)).
6. **Micro-credential tidak berfungsi.** Basis datanya kosong (0 tabel; migrasi tidak dijalankan saat kontainer menyala), `GET /api/micro-cred/tracks` menjawab 500, dan token identity memang tidak diterima layanan itu (akun belum dipindahkan). Putuskan: matikan layanan dan sembunyikan menunya, atau selesaikan pemindahannya.
7. **CI akan gagal.** Langkah `nginx -t` di `.github/workflows/ci.yml` tidak menambahkan host `identity-api` (diuji ulang: `host not found in upstream`).

## Keamanan

| Tingkat | Temuan | Dampak | Perbaikan |
|---|---|---|---|
| Kritis | Postgres (8101), MinIO (8102, 8103), Mailpit (8104, 8105) AlurKerja terbuka di `0.0.0.0` | basis data, berkas, dan email (termasuk tautan sandi) dapat dijangkau dari luar; port Docker sering melewati UFW | bind ke `127.0.0.1` atau jangan dipublikasikan; Mailpit diganti SMTP asli |
| Kritis | `JWT_SECRET` micro-credential memakai nilai bawaan kode, berbeda dari identity | token micro-credential bisa dipalsukan. Gateway menolaknya **hanya karena** secretnya berbeda; bila disamakan seperti anjuran komentar compose, pendaftaran publik micro-credential (bisa memilih peran `advisor`) menghasilkan token yang diterima gateway | matikan rute publik `/api/micro-cred/auth/*`, ganti secret, perbaiki komentar compose |
| Tinggi | `/api/judul-recommender/*` terbuka untuk semua pengguna masuk, tanpa batas | memakai kuota Groq sesuka hati, termasuk `/chat` dengan konteks buatan sendiri, melewati identity | hapus lokasi itu di NGINX (web sudah memakai rute identity; cek dulu `ThesisView` lama di `app/beranda`) |
| Tinggi | Tidak ada pembatasan laju (`limit_req`) di gateway; batas pesan dan obrolan harian brainstorm sudah dihapus | biaya AI (judul dan matkul) tidak terkendali | pasang `limit_req` untuk rute AI dan login; kembalikan batas |
| Tinggi | `POST /api/matkul-recommender/khs/upload` dan `/panduan/extract-upload` hanya butuh token apa pun | panggilan AI dan pemrosesan PDF tanpa batas; rute panduan sudah usang | batasi laju; tutup rute usang |
| Sedang | Klien Keycloak `superapp-sync` (peran `platform_owner`) masih ada | kuasa atas seluruh pengguna AlurKerja bila secretnya bocor | nonaktifkan atau hapus; di VPS jangan dibuat |
| Sedang | Admin Keycloak sementara; sandi owner dan secret pernah tampil di tangkapan layar | akun berkuasa penuh | buat admin permanen; di VPS buat semua sandi dan secret baru |
| Sedang | `PB_ADMIN_PASSWORD` pendek dan bernilai lemah; `POSTGRES_PASSWORD` micro-credential bawaan; `APP_ENV=local` | mudah ditebak | ganti semua di VPS |
| Sedang | Matkul mengembalikan `err.message` ke pemanggil | rincian internal terbaca | kirim pesan umum, rincian di log |
| Rendah | Dokumentasi API (`/api/identity/docs`, `/api/judul-recommender/docs`) terbuka untuk pengguna masuk | memudahkan penjajakan | matikan di produksi |
| Rendah | Judul memakai `allow_origins=["*"]`; CORS gateway hanya berisi origin dev | kecil karena dibalik gateway | rapikan |

## Operasional

- **Cadangan basis data otomatis belum ada** (4 basis data dan volume berkas panduan). Uji pemulihan belum pernah dilakukan dalam audit ini.
- **Log kontainer tidak dibatasi**; atur `max-size` agar disk tidak penuh.
- **Sumber daya:** saat diam, AlurKerja memakai sekitar 2,2 GB RAM dan superapp 0,75 GB. Siapkan VPS minimal 8 GB.
- Jalankan produksi dengan `docker compose -f docker-compose.yml up -d` (tanpa berkas override yang membuka port debug).
- Superadmin pertama: `python -m src.cli buat-superadmin`. Jangan membawa akun dan data uji.
- Gateway menyimpan alamat layanan saat menyala; setelah membangun ulang satu layanan, muat ulang NGINX.
- `.env.example` belum ada untuk layanan judul; contoh identity kurang `ALURKERJA_KEYCLOAK_REALM`, `ALURKERJA_REPORT_TENANT`, `ALURKERJA_WORKSPACE`; contoh connector punya `WORKER_MAX_ATTEMPTS`, `WORKER_RETRY_MS` yang tidak diisi.
- API laporan dan API admin AlurKerja tidak terdokumentasi; kunci versi AlurKerja.

## Belum diperiksa

- Pemindaian kerentanan pustaka (`npm audit`, `pip-audit`) — belum dijalankan. Perlu dilakukan, terutama Next.js di matkul (16.0.10).
- Uji beban, uji penetrasi, dan peninjauan baris per baris seluruh kode.
- Alur lengkap lewat browser dan Tasklist pada putaran audit ini; sebagian diuji pada pengerjaan fitur sebelumnya. Login `daffa@gmail.com` ke AlurKerja belum pernah dibuktikan.
- Tes integrasi micro-credential dan CI di GitHub.
- Hardening server VPS (SSH, firewall, pembaruan OS).

## Urutan yang disarankan

1. Commit pekerjaan.
2. Tutup celah: rute AI langsung dan micro-credential di NGINX, `limit_req`, pesan galat.
3. Putuskan nasib micro-credential.
4. Tambahkan frontend dan reverse proxy HTTPS ke compose; pisahkan konfigurasi produksi.
5. Siapkan AlurKerja di VPS dengan port tertutup, lalu deploy proses, form, dashboard.
6. Cadangan otomatis, batas log, secret baru.
7. Uji dari awal di VPS dengan akun baru.
