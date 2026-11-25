# 06. Draf API

Prefiks publik: `/api/identity/*`. Di balik NGINX, prefiks dibuang sebelum sampai ke layanan. Format galat mengikuti layanan lain: `{"detail": "pesan"}`.

## Auth

| Method | Path | Akses | Fungsi |
|---|---|---|---|
| POST | `/auth/login` | publik | login, mengembalikan access dan refresh token |
| POST | `/auth/refresh` | publik (butuh refresh token) | rotasi token |
| POST | `/auth/logout` | token | cabut refresh token |
| POST | `/auth/ganti-sandi` | token | ganti sandi sendiri |
| GET | `/auth/saya` | token | profil, peran aktif, cakupan unit |

## Struktur organisasi

| Method | Path | Akses |
|---|---|---|
| GET | `/fakultas`, `/fakultas/{id}` | semua yang login |
| POST/PATCH | `/fakultas` | superadmin |
| GET | `/jurusan?fakultas_id=` | semua yang login |
| POST/PATCH | `/jurusan` | superadmin |
| GET | `/prodi?jurusan_id=` | semua yang login |
| POST/PATCH | `/prodi` | superadmin |
| GET | `/struktur` | semua yang login; pohon lengkap fakultas, jurusan, prodi |

Tidak ada DELETE. Unit ditutup dengan `PATCH {"aktif": false}`; ditolak dengan 409 jika masih ada anak aktif atau penugasan aktif.

## Orang dan akun

| Method | Path | Akses |
|---|---|---|
| GET | `/orang?prodi_id=&q=&peran=` | sesuai cakupan |
| GET | `/orang/{id}` | sesuai cakupan |
| POST | `/orang` | superadmin |
| PATCH | `/orang/{id}` | superadmin |
| POST | `/orang/impor` | superadmin; unggah CSV, mengembalikan laporan per baris |
| POST | `/akun` | superadmin; membuat akun untuk orang |
| POST | `/akun/{id}/atur-ulang-sandi` | superadmin |
| PATCH | `/akun/{id}/status` | superadmin |

## Penugasan dan relasi

| Method | Path | Akses |
|---|---|---|
| GET | `/penugasan?unit_id=&peran=&aktif=` | sesuai cakupan |
| POST | `/penugasan` | superadmin (dekan, kajur, kaprodi); kaprodi untuk `dosen_pa` di prodinya |
| POST | `/penugasan/{id}/akhiri` | sama dengan di atas |
| POST | `/keanggotaan` | superadmin, kaprodi (prodinya) |
| POST | `/keanggotaan/{id}/status` | superadmin, kaprodi (prodinya); aktif, cuti, lulus, keluar. Lulus dan keluar menutup keanggotaan dan bimbingan |
| POST | `/keanggotaan/{id}/pindah` | superadmin; menutup lama, membuka baru |
| GET | `/bimbingan?dosen_id=&mahasiswa_id=` | sesuai cakupan |
| POST | `/bimbingan` | superadmin, kaprodi |
| POST | `/bimbingan/{id}/akhiri` | superadmin, kaprodi |
| POST | `/bimbingan/pindahkan` | superadmin, kaprodi; mengalihkan banyak mahasiswa ke PA lain sekaligus |

## Panduan akademik

| Method | Path | Akses |
|---|---|---|
| GET | `/prodi/{id}/panduan` | semua yang login; daftar versi |
| GET | `/prodi/{id}/panduan/aktif` | semua yang login |
| POST | `/prodi/{id}/panduan` | superadmin, kaprodi; unggah sebagai `draf`. Teks diekstrak saat unggah; PDF scan atau rusak ditolak 422 |
| POST | `/panduan/{id}/aktifkan` | superadmin, kaprodi; mengarsipkan versi aktif sebelumnya |
| GET | `/panduan/{id}/berkas` | semua yang login |

## Konteks akademik (dipakai matkul)

| Method | Path | Akses |
|---|---|---|
| GET | `/akademik/konteks?tanpa_teks=&prodi_id=` | mahasiswa (prodinya sendiri); staf wajib `prodi_id` dalam cakupan. Detail di [11](11-integrasi-matkul.md) |

## Audit

| Method | Path | Akses |
|---|---|---|
| GET | `/audit?objek_id=&pelaku_id=&dari=&sampai=` | superadmin |

## Contoh

```http
POST /api/identity/penugasan
Authorization: Bearer <token superadmin>
Content-Type: application/json

{ "orang_id": "…", "peran": "kaprodi", "unit_tipe": "prodi", "unit_id": "…", "mulai": "2026-12-01" }
```

Respons 409 jika prodi itu sudah punya kaprodi aktif:

```json
{ "detail": "Prodi ini sudah memiliki kaprodi aktif. Akhiri penugasan lama terlebih dahulu." }
```

## Kode galat

| Status | Arti |
|---|---|
| 400 | data tidak valid (misal peran dan tipe unit tidak cocok) |
| 401 | token tidak ada, rusak, atau kedaluwarsa |
| 403 | peran atau cakupan tidak cukup |
| 404 | tidak ditemukan, atau di luar cakupan (sengaja sama, agar tidak membocorkan keberadaan data) |
| 409 | melanggar aturan jumlah (satu kaprodi aktif, satu PA aktif, dst.) |
| 422 | validasi skema |
| 429 | terlalu banyak percobaan login |

## Pagination

Daftar memakai `?halaman=1&ukuran=50` (maksimal 200). Respons: `{"data": [...], "total": n}`.
