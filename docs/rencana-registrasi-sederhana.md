# Rencana: Registrasi Sederhana dan Prodi Dummy

Dokumen serah terima untuk agen pelaksana. Ditulis 27 Nov 2026. **Belum ada kode yang diubah untuk rencana ini.**

## 1. Aturan kerja (wajib)

1. Repo `superapp-gateway`, branch `feat/hackathon-superapp-gateway`. **Jangan commit atau push** tanpa diminta pemilik proyek.
2. Folder kerja berisi **perubahan pemilik yang belum di-commit** (web, identity `judul.py`/`pengajuan.py`, matkul, `deploy/deploy-vps.sh`, berkas baru di `frontend/`). Bangun di atasnya. Jangan `git checkout`, `reset`, `stash`, atau menimpa berkas secara utuh.
3. Jangan menulis sandi, token, atau isi `.env` ke kode, dokumen, log, atau keluaran. Sandi akun dummy diketik pengguna di formulir; jangan ditanam.
4. **Jangan deploy ke server** tanpa diminta. Hari ini dalam masa presentasi (27 Nov–1 Des 2026).
5. Komunikasi dengan pemilik proyek dalam bahasa Indonesia.
6. Ikuti gaya kode yang ada (nama berbahasa Indonesia, audit lewat `src/domain/audit.py`, galat lewat `src/api/errors.py`).

## 2. Kebutuhan

| No | Kebutuhan |
|---|---|
| K1 | Halaman registrasi sederhana: nama, username, sandi, program studi, perguruan tinggi. Nama bebas. |
| K2 | Struktur DB diubah seminimal mungkin. Pendaftar ditampung di fakultas, jurusan, dan prodi **dummy** pada struktur yang ada. |
| K3 | Isian program studi dan perguruan tinggi disimpan di data orang, **hanya sebagai catatan**. |
| K4 | Prodi dummy punya **satu akun dosen** yang merangkap **dosen PA dan kaprodi**. |
| K5 | Setiap mahasiswa prodi dummy otomatis tertaut ke dosen itu. |
| K6 | Pembuat mahasiswa dummy **lewat UI di dalam prodi dummy**: jumlah bebas (100, 110, ...), nama berawalan "Mahasiswa", email otomatis, sandi diisi di formulir dan **final** (tanpa wajib ganti). |
| K7 | Prodi dummy **tidak** memakai panduan unggahan prodi. **Setiap pengguna mengunggah panduan akademiknya sendiri.** |

Di luar cakupan: verifikasi email, lupa sandi, CAPTCHA, perubahan BPMN, microcred, perubahan prodi FTI asli.

## 3. Asumsi (belum dikonfirmasi pemilik)

Jalankan sesuai asumsi, sebutkan di laporan akhir.

| No | Asumsi |
|---|---|
| A1 | Pemilik menulis "Namauser". Ditafsirkan sebagai nama lengkap **dan** username. Email akun = `<username>@studentgateway.id`; login boleh mengetik username saja. |
| A2 | Dosen dummy adalah akun baru, bukan salah satu dari 122 dosen FTI. Pemilik menambahkannya di AlurKerja secara manual. |
| A3 | Prodi selain dummy tetap memakai panduan dari kaprodi, tanpa perubahan perilaku. |
| A4 | Panduan pribadi hanya dapat diunduh pemiliknya, dosen PA aktifnya, dan superadmin. |
| A5 | Registrasi punya sakelar buka/tutup (bawaan tutup) dan pembatas laju. |
| A6 | Nama buatan UI berbentuk `Mahasiswa 001`, email `mahasiswa001@studentgateway.id`, nomor berlanjut. |

## 4. Perilaku sekarang (hasil pembacaan kode)

- Tidak ada registrasi di identity; akun dibuat superadmin. Teks di `frontend/components/login-view.tsx` menyatakan hal itu, dan input login bertipe `email`.
- `LoginIn.email` sengaja `str` biasa (`services/identity/src/api/schemas.py`).
- `terbitkan_token` menolak akun tanpa peran aktif; keanggotaan prodi memberi peran `mahasiswa` (`domain/cakupan.py`).
- Panduan melekat pada prodi: satu aktif per prodi (`uq_panduan_aktif`), versi unik per prodi (`uq_panduan_versi`), berkas di `PANDUAN_DIR/<prodi_id>/v<versi>.pdf`, kelola hanya `kelola_prodi` (`routes/panduan.py`).
- `GET /panduan/{id}/berkas`, `/prodi/{id}/panduan`, dan `/prodi/{id}/panduan/aktif` terbuka untuk semua akun yang login.
- Pengajuan rencana studi menolak bila mahasiswa tidak punya panduan aktif, bimbingan aktif, atau akun DPA (`routes/pengajuan.py`, fungsi `ajukan`).
- Proses AlurKerja hanya membawa email DPA dan NIM; mahasiswa tidak perlu akun AlurKerja.
- Matkul mengambil panduan dari `GET /akademik/konteks` (interaktif) dan `GET /internal/pengajuan/{id}/konteks` (proses). Cache pratinjau berkunci `(sidik KHS, NIM, panduan_id)`, jadi **NIM harus ada dan unik**. NIM pada KHS tidak divalidasi terhadap NIM akun.
- Judul tugas akhir: mahasiswa boleh memilih dosen PA atau kaprodi prodinya, jadi satu dosen dummy cukup.
- Rute jalur: browser → NGINX server → Next (`rewrites` `/api/*`) → NGINX gateway → layanan. Gateway menolak semua rute tanpa token kecuali yang diberi `auth_request off`.

## 5. Basis data: migrasi `0007`

Berkas baru `services/identity/alembic/versions/0007_registrasi.py` (`down_revision = "0006"`), dengan `upgrade` dan `downgrade` (uji menjalankan downgrade ke base). Samakan `src/models.py`.

| Tabel | Perubahan |
|---|---|
| `orang` | `prodi_isian VARCHAR(200) NULL`, `pt_isian VARCHAR(200) NULL` |
| `panduan_akademik` | `pemilik_id UUID NULL` FK `orang.id` (`ON DELETE RESTRICT`), terindeks. `NULL` = panduan prodi (perilaku lama) |
| indeks aktif | ganti `uq_panduan_aktif` menjadi unik `(prodi_id)` `WHERE status='aktif' AND pemilik_id IS NULL`; tambah `uq_panduan_aktif_pemilik` unik `(pemilik_id)` `WHERE status='aktif' AND pemilik_id IS NOT NULL` |
| versi | ganti constraint `uq_panduan_versi` menjadi indeks unik `(prodi_id, versi) WHERE pemilik_id IS NULL`; tambah `(pemilik_id, versi) WHERE pemilik_id IS NOT NULL` |

Perbarui pemetaan pesan di `src/api/errors.py` (`PESAN_BATASAN`) untuk nama indeks baru.

Downgrade harus menghapus baris panduan pribadi lebih dulu (atau gagal dengan pesan jelas).

## 6. Konfigurasi prodi dummy

Tanpa kolom penanda baru. Tambah di `src/core/config.py` dan `services/identity/.env.example`:

| Variabel | Bawaan | Arti |
|---|---|---|
| `REGISTRASI_AKTIF` | `false` | sakelar registrasi publik |
| `PRODI_TERBUKA` | kosong | jalur kode `FAKULTAS/JURUSAN/PRODI` prodi dummy, contoh `DUMMY/UMUM/UMUM` |
| `REGISTRASI_MAKS_PER_JAM` | `100` | batas pendaftaran berhasil per jam, seluruh layanan |
| `DUMMY_MAKS_SEKALI` | `300` | batas jumlah sekali buat |

Kosongnya `PRODI_TERBUKA` mematikan registrasi, pembuat dummy, dan aturan panduan pribadi. Buat fungsi tunggal, misalnya `src/domain/prodi_terbuka.py`: `prodi_terbuka(db) -> Prodi | None` memakai `_cari_prodi_dari_jalur` (pindahkan dari `routes/orang.py` ke domain), dan `dosen_terbuka(db, prodi, hari) -> Orang | None`.

**Dosen prodi dummy** = pemegang penugasan `kaprodi` aktif prodi itu, yang juga punya penugasan `dosen_pa` aktif pada prodi itu dan akun aktif. Bila tidak ada, registrasi dan pembuat dummy menjawab 503 dengan pesan jelas. Jangan membuat mahasiswa tanpa pembimbing.

## 7. Backend identity

### 7.1 Satu fungsi pembuat mahasiswa

Dipakai registrasi dan pembuat dummy, dalam satu transaksi:

1. `Orang` (nama, `nim`, `prodi_isian`, `pt_isian`)
2. `Akun` (`wajib_ganti_sandi=False`)
3. `KeanggotaanProdi` (prodi dummy, angkatan = tahun berjalan, status `aktif`, `mulai` = hari ini)
4. `Bimbingan` (dosen dummy)
5. catatan audit untuk tiap objek (tanpa sandi atau hash)

NIM otomatis dan unik, misalnya `98` + tahun 2 angka + 6 angka urut (dosen dummy memakai awalan `99` pada NIDN). Tangani bentrok dengan mencoba ulang di savepoint.

### 7.2 `GET /auth/registrasi` (publik)

Kembalikan `{"aktif": bool}`. Dipakai web untuk menampilkan atau menyembunyikan tautan daftar.

### 7.3 `POST /auth/register` (publik)

Isian: `nama_lengkap` (1–200), `username` (`^[a-z0-9._-]{3,32}$`, diubah ke huruf kecil), `sandi` (`validasi_kebijakan_sandi`, minimal 10), `program_studi` (1–200), `perguruan_tinggi` (1–200). Skema turunan `Dasar` (`extra="forbid"`), sehingga klien tidak bisa menyisipkan peran, prodi, atau pemilik.

- Mati (`REGISTRASI_AKTIF=false` atau prodi kosong) → 404.
- Username terpakai → 409 dengan pesan jelas. Tolak juga username cadangan (`admin`, `superadmin`, awalan `mahasiswa` diikuti angka agar tidak bentrok dengan pembuat dummy, dan nama dosen yang sudah terdaftar lewat pemeriksaan email unik).
- Berhasil → 201 dengan `TokenOut` (langsung masuk).

**Pembatas laju:** gateway melihat alamat container frontend, bukan alamat pengunjung (`X-Real-IP` ditimpa NGINX gateway). Jadi batas per IP **tidak bisa dipercaya** tanpa mengubah rantai proxy. Pakai batas global per jam (`REGISTRASI_MAKS_PER_JAM`) di memori, seperti pembatas login di `api/deps.py`, dan tambahkan ke `reset_semua_pembatas()`. Bila ingin batas per IP, tambahkan `limit_req` di NGINX server (`deploy/nginx-superapp.conf`, lokasi khusus `/api/identity/auth/register`), karena di sanalah alamat asli terlihat.

### 7.4 Login dengan username

Di `login`: bila isian tidak mengandung `@`, tambahkan `@studentgateway.id`. Lakukan **sebelum** menyusun kunci pembatas.

### 7.5 `POST /prodi/{pid}/mahasiswa-dummy` (superadmin)

Isian: `jumlah` (1–`DUMMY_MAKS_SEKALI`), `sandi` (kebijakan sandi). Tolak 400 bila `pid` bukan prodi dummy.

- Nomor lanjut dari angka tertinggi pada email `mahasiswa<angka>@studentgateway.id`; minimal 3 digit.
- `prodi_isian` dan `pt_isian` diisi teks dummy yang jelas.
- Hash bcrypt (biaya 12) sekitar 0,2–0,3 detik per akun. Karena sandinya sama, **boleh menghitung satu hash dan memakainya untuk semua akun batch itu**, supaya 100+ akun tidak melewati batas waktu proxy (gateway identity 60 detik).
- Respons: `{"dibuat": n, "akun": [{"nama": ..., "email": ...}]}`. Jangan kembalikan sandi.
- Aturan gateway: `POST /api/identity/prodi/{pid}/mahasiswa-dummy` tidak cocok dengan pola superadmin di `gateway/auth/app.py` (`prodi(/[^/]+)?$`), jadi pemeriksaan superadmin **wajib** di route (`Superadmin` dari `api/deps.py`).

### 7.6 Panduan pribadi

Aturan tunggal, satu fungsi, misalnya `panduan_berlaku(db, prodi_id, mahasiswa_id)`:

- prodi dummy → panduan aktif dengan `pemilik_id = mahasiswa_id`;
- prodi lain → panduan aktif dengan `pemilik_id IS NULL`.

Ganti **semua** pemakaian "panduan aktif prodi":

| Berkas | Catatan |
|---|---|
| `routes/akademik.py` `konteks` | pesan 404 untuk prodi dummy: minta pengguna mengunggah panduannya. Staf yang melihat prodi dummy tidak punya panduan prodi |
| `routes/internal.py` `konteks_pengajuan` | memakai `p.mahasiswa_id` |
| `routes/pengajuan.py` `ajukan` | pesan 409 diganti sesuai prodi |
| `routes/pengajuan.py` `_keluaran` | `versi_aktif_sekarang` memakai pemilik yang sama |
| `routes/panduan.py` daftar, aktif, unggah, aktifkan | daftar dan aktif per prodi hanya `pemilik_id IS NULL`; unggah oleh pengelola prodi pada prodi dummy ditolak 409; `aktifkan` menolak panduan pribadi milik orang lain |
| `routes/ringkasan.py` | prodi dummy tidak masuk `prodi_tanpa_panduan` |
| `routes/struktur.py`, `cli.py` | periksa apakah ada pemakaian panduan lain |

Endpoint baru:

| Metode | Rute | Perilaku |
|---|---|---|
| GET | `/panduan/saya` | daftar versi milik pengguna, terbaru dulu |
| POST | `/panduan/saya` | mahasiswa prodi dummy mengunggah PDF; validasi dan ekstraksi teks sama dengan unggahan prodi; **langsung aktif**, versi lama diarsipkan, dalam satu transaksi dengan penguncian baris `orang` |

Detail wajib:

- Jalur berkas pribadi harus memuat pemilik, misalnya `<prodi_id>/<orang_id>/v<n>.pdf`. Jalur lama akan saling menimpa.
- Nomor versi dihitung per pemilik.
- `GET /panduan/{id}/berkas`: untuk panduan pribadi hanya pemilik, dosen PA aktif pemilik, dan superadmin; lainnya 404. Panduan prodi tetap seperti sekarang.
- Batasi jumlah versi per pengguna (misalnya 5) agar disk server tidak penuh. Ukuran per berkas mengikuti `PANDUAN_MAKS_MB`.

### 7.7 Profil dan daftar orang

- Tambahkan `prodi_isian` dan `pt_isian` ke `OrangOut`, `_keluaran` di `routes/orang.py`, dan `GET /auth/saya`. Hanya superadmin dan orang itu sendiri yang menerimanya.
- Periksa tempat lain yang menyusun objek orang secara manual (`routes/penugasan.py`).

## 8. Gateway

Di `gateway/nginx/nginx.conf`, tambah dua rute publik meniru `location = /api/identity/auth/login`: `/api/identity/auth/register` (hanya POST) dan `/api/identity/auth/registrasi` (hanya GET/HEAD). Di `gateway/auth/app.py` tidak ada perubahan. Periksa apakah `gateway/tests/baseline/nginx-noauth.conf` perlu disamakan.

## 9. Web (frontend)

Next di repo ini versi 16; ikuti pola komponen yang sudah ada (antd di admin, komponen sendiri di login dan matkul). Pertahankan branding buatan pemilik (`components/brand.tsx`).

| Bagian | Pekerjaan |
|---|---|
| `app/daftar/page.tsx` (baru) | formulir 5 isian + konfirmasi sandi; setelah sukses simpan token dan ke `/beranda`. Tampilan senada halaman login |
| `components/login-view.tsx` | input menjadi "Email atau username" (`type="text"`); tautan "Daftar" hanya bila registrasi aktif; ganti teks "Akun dibuat oleh admin kampus" |
| `src/services/auth-service.ts` | `register`, `statusRegistrasi` (`auth: false`); perbarui komentar "tidak ada pendaftaran mandiri" |
| `app/robots.ts`, metadata | sesuaikan `/daftar` |
| `components/course-recommendation.tsx` langkah 4 | untuk prodi dummy: belum ada panduan → kotak unggah PDF; sudah ada → info panduan + "Ganti panduan". Teks "Anda tidak perlu mengunggahnya" hanya untuk prodi lain |
| `components/course-dashboard.tsx`, `submit-card.tsx` | ajakan mengunggah panduan; teks "Panduan prodi sudah diperbarui" disesuaikan |
| `src/services/khs-services.ts` | unggah panduan; `getGuide` perlu tahu apakah pengguna boleh mengunggah (kirim `panduan_pribadi: bool` dari `/akademik/konteks` atau `/auth/saya`, juga saat panduan belum ada) |
| `components/admin/prodi-detail.tsx` | di prodi dummy: tab "Panduan akademik" diganti keterangan bahwa panduan diunggah tiap pengguna; tombol "Buat mahasiswa dummy" di tab Mahasiswa (superadmin) |
| `components/admin/tab-mahasiswa-prodi.tsx` | modal jumlah + sandi + konfirmasi; hasil berupa tabel dan unduh CSV (nama, email); cegah klik ganda. Tampilkan kolom prodi isian dan perguruan tinggi. Daftar saat ini mengambil 200 baris: tambahkan paginasi server |
| `components/admin/tab-orang.tsx` | tampilkan prodi isian dan perguruan tinggi |

API perlu memberi tahu web bahwa sebuah prodi adalah prodi dummy, misalnya `terbuka: bool` pada `GET /prodi/{pid}`.

Cegah **injeksi rumus CSV** pada unduhan (nilai berawalan `=`, `+`, `-`, `@`).

## 10. Matkul

Diperkirakan tidak perlu perubahan logika karena sumber panduan tetap dari identity. Yang perlu diperiksa:

- `src/lib/konteks.ts` `peringatanKonteks` membandingkan prodi di KHS dengan nama prodi akun. Pengguna dummy akan selalu mendapat peringatan "berbeda dengan prodi akun". Lewati peringatan itu untuk prodi dummy (perlu penanda di respons konteks) dan sebut "panduan yang Anda unggah".
- Teks prompt `PANDUAN AKADEMIK PROGRAM STUDI <nama prodi>` di `app/api/rekomendasi/route.ts` akan menyebut nama prodi dummy. Untuk panduan pribadi, jangan sebut nama itu.
- Hasil rekomendasi di web menulis "Dasar rekomendasi: Panduan akademik Prodi ..."; sesuaikan.

Berkas matkul punya perubahan pemilik yang belum di-commit; sunting seperlunya saja.

## 11. Urutan kerja

1. Migrasi, model, konfigurasi, fungsi domain.
2. Registrasi, login username, pembuat dummy, beserta uji.
3. Panduan pribadi di identity, beserta uji.
4. Rute gateway.
5. Web: daftar dan login → unggah panduan → admin.
6. Penyesuaian teks matkul.
7. Uji lokal menyeluruh. Laporkan, lalu tunggu perintah deploy.

Bila waktu sempit, urutan nilai demo: 1, 2, 4, daftar/login, pembuat dummy di admin, lalu panduan pribadi. Pengajuan rencana studi mahasiswa dummy **tidak jalan** sebelum panduan pribadi selesai.

## 12. Pengujian

Uji identity memakai Postgres sungguhan (lihat `services/identity/README.md`). Tambahkan tabel baru ke fixture bila ada, dan jangan arahkan ke data sungguhan.

Kasus minimal:

- registrasi: sukses (akun, keanggotaan, bimbingan, tanpa wajib ganti, isian tersimpan); mati → 404; prodi/dosen belum siap → 503; username bentrok → 409; username tidak sah, sandi pendek, field tambahan → 422/400; batas per jam → 429;
- login dengan username dan dengan email; pembatas login tetap bekerja;
- dummy: hanya superadmin; hanya prodi dummy; nomor berlanjut pada pemanggilan kedua; batas jumlah; login berhasil; sandi tidak ada di respons atau audit;
- panduan: pribadi tidak terlihat mahasiswa lain (unduh → 404); DPA dan superadmin bisa; dua pengguna masing-masing punya versi 1 tanpa bentrok berkas; unggah baru mengarsipkan yang lama; konteks, pengajuan, dan internal memakai panduan pemilik; prodi biasa berperilaku seperti semula;
- semua uji lama tetap lulus; migrasi naik dan turun.

Selain itu: `npx tsc --noEmit` dan `pnpm test` di `frontend`; uji matkul yang ada; `nginx -t` pada konfigurasi gateway.

Alur manual lokal: daftar → unggah panduan → unggah KHS → rekomendasi → ajukan → dosen dummy menyetujui → pengajuan judul → dosen menyetujui.

## 13. Deploy dan penyiapan data (hanya bila diminta)

Lihat `docs/deploy-vps.md`. Perubahan belum di-commit dikirim dengan `IKUT_BELUM_COMMIT=1 ./deploy/deploy-vps.sh` dari Git Bash; **tanpa variabel itu server kembali ke HEAD** dan kehilangan perubahan yang sekarang aktif. Migrasi berjalan otomatis saat container identity start; skrip deploy mencadangkan basis data.

Setelah deploy:

1. Admin → Struktur: buat fakultas, jurusan, prodi dummy (kode sesuai `PRODI_TERBUKA`).
2. Buat satu orang dan akun dosen dummy, beri penugasan **dosen PA** dan **kaprodi** pada prodi itu. Akun baru wajib ganti sandi saat login pertama; pemilik mengurusnya sendiri.
3. Pemilik menambahkan dosen itu di AlurKerja (`/admin/users`) dengan **email yang sama persis, huruf kecil**. Sinkron otomatis sengaja dimatikan.
4. Isi `REGISTRASI_AKTIF` dan `PRODI_TERBUKA` di `~/superapp/env/services/identity/.env` (salin juga ke rilis aktif atau deploy ulang).
5. Verifikasi rute publik, satu registrasi uji, satu alur pengajuan.

Jangan deploy menjelang jadwal tampil: tepat setelah deploy terakhir, tab analitik sempat gagal beberapa menit.

## 14. Risiko yang harus disampaikan ke pemilik

| Risiko | Catatan |
|---|---|
| Registrasi publik memakai kuota AI (OpenAI/Groq) | sakelar dan batas per jam; tutup setelah presentasi |
| Sandi dummy bersama dan mudah ditebak | pakai sandi kuat; akun dapat ditangguhkan dari admin |
| Pendaftar bebas menulis nama dan isian | tampil di admin dan halaman dosen |
| Analitik tidak dibatasi per prodi | dosen dummy sebagai kaprodi melihat rekap seluruh prodi (tanpa identitas mahasiswa), dan data dummy ikut terhitung |
| Disk server (pemakaian ±39%) | batasi ukuran dan jumlah versi panduan |
| Pendaftaran Keycloak AlurKerja masih terbuka saat dicek 26 Nov | di luar rencana ini; ingatkan pemilik |

## 15. Kriteria selesai

- [ ] K1–K7 berjalan di lokal.
- [ ] Prodi FTI asli berperilaku sama seperti sebelumnya.
- [ ] Panduan pribadi tidak dapat diakses pengguna lain.
- [ ] Registrasi mati secara bawaan dan bisa dimatikan lewat konfigurasi.
- [ ] Semua uji lulus; hasilnya dilaporkan apa adanya.
- [ ] `docs/identity` diperbarui (API, model data) tanpa nilai rahasia.
- [ ] Tidak ada commit, push, atau deploy tanpa perintah.
