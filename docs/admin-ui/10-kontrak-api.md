# 10. Kontrak API yang dipakai halaman admin

Semua lewat gateway: awalan `/api/identity` (NGINX meneruskan `/api/identity/x` → `/x` di layanan identity). Semua butuh `Authorization: Bearer <access token>` kecuali login/refresh. **Gunakan `adminService`** (`src/services/admin-service.ts`); tipe TypeScript di sana sudah sesuai dengan ini. Sumber kebenaran skema: `services/identity/src/api/schemas.py` dan `services/identity/src/api/routes/*.py`.

## Konvensi

- Daftar: `{ data: T[], total: number }`; parameter `halaman` (≥1, bawaan 1), `ukuran` (1–200, bawaan 50). Tanpa paginasi untuk `/struktur` dan `/prodi/{id}/panduan`.
- Galat: JSON `{"detail": "<pesan Indonesia>"}`; galat validasi (422) berbentuk daftar `detail[].msg` + `loc`. `apiFetch` sudah mengubahnya menjadi `ApiError.message`.
- UUID untuk semua id. Tanggal: `YYYY-MM-DD`. Waktu: ISO 8601.
- 401 → `apiFetch` mencoba refresh token sekali; bila gagal mengalihkan ke `/login`. 403 → tampilkan pesan, jangan logout.

## Struktur

| Method | Path | Isi permintaan | Jawaban | Akses |
|---|---|---|---|---|
| GET | `/struktur?semua=true` | — | `[{id,kode,nama,aktif,jurusan:[{id,kode,nama,aktif,prodi:[{id,kode,nama,jenjang,aktif}]}]}]` (tanpa `maks_sks_semester`) | login |
| GET | `/fakultas` `/jurusan` `/prodi` | filter `aktif`, `fakultas_id`/`jurusan_id` | daftar | login |
| GET | `/prodi/{id}` | — | `{id,jurusan_id,kode,nama,jenjang,maks_sks_semester,aktif}` | login |
| POST | `/fakultas` | `{kode,nama}` | Fakultas | superadmin |
| POST | `/jurusan` | `{fakultas_id,kode,nama}` | Jurusan | superadmin |
| POST | `/prodi` | `{jurusan_id,kode,nama,jenjang,maks_sks_semester?}` | Prodi | superadmin |
| PATCH | `/fakultas/{id}` `/jurusan/{id}` | `{nama?,aktif?}` | objek | superadmin |
| PATCH | `/prodi/{id}` | `{nama?,jenjang?,maks_sks_semester?,aktif?}` | Prodi | superadmin |

**Peringatan PATCH prodi:** `maks_sks_semester` yang **ada** di badan (walau `null`) berarti "ubah/kosongkan"; yang **tidak ada** berarti "biarkan". Jangan mengirimnya kecuali memang diubah.

Aturan: `kode` `^[A-Za-z0-9._-]+$` 1–32; `nama` 1–200; `jenjang` ∈ `D3|S1|S2|S3|Profesi`; `maks_sks_semester` 1–40 atau null.

## Orang dan akun

| Method | Path | Isi | Jawaban | Akses |
|---|---|---|---|---|
| GET | `/orang?q=&prodi_id=&peran=` | — | `{data:[Orang],total}` | login (cakupan terbatas untuk non-superadmin) |
| GET | `/orang/{id}` | — | `Orang` | login (dalam cakupan) |
| POST | `/orang` | `{nama_lengkap,nim?,nidn?,email_kontak?}` | `Orang` | superadmin |
| PATCH | `/orang/{id}` | sama, semua opsional | `Orang` | superadmin |
| POST | `/orang/impor` | multipart `berkas` (CSV ≤2 MB) | `{total,berhasil,gagal,baris:[{baris,status,alasan?,email?,sandi_sementara?}]}` | superadmin |
| POST | `/akun` | `{orang_id,email,sandi?}` | `Akun` (`sandi_sementara` bila dibuat otomatis) | superadmin |
| POST | `/akun/{id}/atur-ulang-sandi` | — | `Akun` (`sandi_sementara` selalu ada) | superadmin |
| PATCH | `/akun/{id}/status` | `{status: aktif|ditangguhkan|nonaktif}` | `Akun` | superadmin |

`Orang`: `{id,nama_lengkap,nim,nidn,email_kontak,peran:string[],akun:{id,email,status,wajib_ganti_sandi}|null}` (`peran` termasuk `mahasiswa` bila punya keanggotaan prodi aktif).
`Akun`: `{id,orang_id,email,status,wajib_ganti_sandi,sandi_sementara|null}`.
Filter `peran` pada `/orang`: `^(superadmin|dekan|kajur|kaprodi|dosen_pa|mahasiswa)$`; `q` ≤ 100 karakter.

## Penugasan dan keanggotaan

| Method | Path | Isi | Akses |
|---|---|---|---|
| GET | `/penugasan?orang_id=&unit_id=&peran=&aktif=` | — | login (non-superadmin: miliknya + unit dalam cakupan) |
| POST | `/penugasan` | `{orang_id,peran,unit_tipe,unit_id|null,mulai?}` | superadmin; kaprodi hanya `dosen_pa` pada `prodi` miliknya |
| POST | `/penugasan/{id}/akhiri` | `{selesai?: date|null}` | sama |
| GET | `/keanggotaan?orang_id=&prodi_id=&aktif=` | — | login (dalam cakupan) |
| POST | `/keanggotaan` | `{orang_id,prodi_id,angkatan?,status?: aktif|cuti,mulai?}` | superadmin / kaprodi prodi itu |
| POST | `/keanggotaan/{id}/status` | `{status: aktif|cuti|lulus|keluar,tanggal?}` | cakupan; `lulus`/`keluar` menghentikan bimbingan & pengajuan |
| POST | `/keanggotaan/{id}/pindah` | `{prodi_tujuan_id,angkatan?,tanggal?}` | **superadmin saja** |

`Penugasan`: `{id,orang_id,peran,unit_tipe,unit_id,mulai,selesai}`. `Keanggotaan`: `{id,orang_id,prodi_id,angkatan,status,mulai,selesai}`.
Pasangan peran–unit sah: lihat [08](08-penugasan-dan-dpa.md). `unit_id` wajib untuk non-global dan harus null untuk global (server 422 bila salah).

## Bimbingan (DPA)

| Method | Path | Isi | Jawaban |
|---|---|---|---|
| GET | `/bimbingan?dosen_id=&mahasiswa_id=&aktif=` | — | `{data:[{id,dosen_id,mahasiswa_id,mulai,selesai}],total}` |
| POST | `/bimbingan` | `{dosen_id,mahasiswa_id,mulai?}` | `Bimbingan` |
| POST | `/bimbingan/{id}/akhiri` | `{selesai?}` (kirim `{}`) | `Bimbingan` |
| POST | `/bimbingan/pindahkan` | `{dosen_asal_id,dosen_tujuan_id,mahasiswa_ids?}` | `{dialihkan:n,bimbingan_baru:[id]}` |

Akses: superadmin atau kaprodi prodi mahasiswa (`kelola_prodi`). Atomik untuk `/pindahkan`.

## Panduan

| Method | Path | Isi | Jawaban |
|---|---|---|---|
| GET | `/prodi/{id}/panduan` | — | `{data:[Panduan],total}` |
| GET | `/prodi/{id}/panduan/aktif` | — | `Panduan` atau 404 |
| POST | `/prodi/{id}/panduan` | multipart: `judul` (≤300), `berlaku_mulai?` (date), `berkas` (PDF ≤ 20 MB) | `Panduan` (status `draf`) |
| POST | `/panduan/{id}/aktifkan` | — | `Panduan` |
| GET | `/panduan/{id}/berkas` | — | PDF (`application/pdf`); **butuh token** → ambil sebagai Blob |

`Panduan`: `{id,prodi_id,versi,judul,berlaku_mulai,status,berkas_nama,teks_karakter}`. Akses unggah/aktifkan: superadmin atau kaprodi prodi itu.

## Audit

| Method | Path | Keterangan |
|---|---|---|
| GET | `/audit?aksi=&pelaku_id=&objek_id=&dari=&sampai=&halaman=&ukuran=` | superadmin saja; `{data:[{id,pelaku_id,aksi,objek_tipe,objek_id,sebelum,sesudah,waktu}],total}` urut terbaru |

## Profil (untuk shell)

`GET /auth/saya` → `{id,nama_lengkap,nim,email,wajib_ganti_sandi,peran:string[],akademik:{prodi:{nama},fakultas:{nama}|null}|null,...}`. Sudah dibungkus `authService.me()` / `useCurrentUser()`.

## Yang **tidak** disediakan API (jangan berharap)

- Cakupan kaprodi (prodi mana yang ia pimpin) tidak ada di `/auth/saya`. Caranya mengetahui: `GET /penugasan?orang_id=<id saya>&aktif=true` (pengguna boleh melihat penugasan miliknya sendiri), ambil yang `peran=kaprodi` → `unit_id` = prodi yang dikelola. Lihat [11](11-hak-akses.md).
- Tidak ada endpoint hapus untuk struktur, orang, akun, panduan. Nonaktifkan/arsipkan saja.
- Tidak ada pencarian prodi berdasarkan nama di server; filter di klien dari `/struktur`.
