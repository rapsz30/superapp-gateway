# 06. Halaman Beranda (ringkasan) dan Struktur

## Beranda: `/admin/beranda`

Halaman baru (belum ada padanannya sekarang). Tujuan: orientasi cepat dan jalan pintas.

### Isi (usulan; lihat "Terbuka" di [02](02-keputusan-desain.md))

Baris kartu statistik (`Row`/`Col` + `Card` + `Statistic`), semuanya dari endpoint yang **sudah ada**, memakai nilai `total`:

| Kartu | Sumber | Catatan |
|---|---|---|
| Fakultas aktif | `GET /fakultas?aktif=true&ukuran=1` → `total` | |
| Jurusan aktif | `GET /jurusan?aktif=true&ukuran=1` → `total` | |
| Program studi aktif | `GET /prodi?aktif=true&ukuran=1` → `total` | |
| Orang terdaftar | `GET /orang?ukuran=1` → `total` | untuk non-superadmin yang tampak hanya yang dalam cakupannya |
| Bimbingan DPA aktif | `GET /bimbingan?aktif=true&ukuran=1` → `total` | |
| Prodi tanpa panduan aktif | hitung: untuk tiap prodi aktif panggil `GET /prodi/{id}/panduan/aktif`; 404 = belum ada | batasi (mis. maks 50 prodi) agar tidak menembak server; tampilkan sebagai `Alert type="warning"` dengan daftar prodi dan tautan ke `/admin/panduan` |

Di bawahnya: "Mulai cepat" (`Steps` atau daftar `Card`) yang menautkan urutan penyiapan: **Struktur → Panduan → Orang → Penugasan → DPA**. Beri tanda selesai bila data sudah ada (struktur ada ≥ 1 prodi, dst.). Ini membantu superadmin baru.

Kartu yang gagal dimuat tidak boleh merobohkan halaman: tampilkan `—` dan `Alert` kecil.

Superadmin saja yang melihat kartu "Orang terdaftar" bila angka itu menyesatkan untuk peran lain (cakupan terbatas). Boleh juga disembunyikan dari non-superadmin.

## Struktur: `/admin/struktur`

Padanan: `components/admin/tab-struktur.tsx`.

### Data

`useStruktur().pohon` (dari `GET /struktur?semua=true`): array fakultas → `jurusan[]` → `prodi[]`. Tiap node: `{ id, kode, nama, aktif }`, prodi juga `jenjang`. **Tidak memuat `maks_sks_semester`** (lihat jebakan di [01](01-keadaan-sekarang.md)).

### Tampilan yang disarankan

`Tree` (`treeData` dari pohon, `defaultExpandAll`, `blockNode`) dengan `titleRender`: nama (tebal untuk fakultas), `Tag` kode, `Tag` jenjang untuk prodi, `Tag color="red"` "nonaktif", dan di kanan tombol aksi kecil (hanya `isSuper`). Alternatif yang sama baiknya: `Table` dengan `expandable` bertingkat. Pilih satu; pastikan baris panjang tidak menabrak aksi di ponsel.

Tombol di header halaman: `+ Fakultas` (hanya superadmin).

### Aksi (hanya `isSuper`; yang lain melihat `Alert type="info"` "Hanya superadmin yang dapat mengubah struktur")

| Aksi | Panggilan | Perilaku |
|---|---|---|
| + Fakultas | `POST /fakultas {kode, nama}` | form di `Modal` |
| + Jurusan (di fakultas) | `POST /jurusan {fakultas_id, kode, nama}` | judul modal menyebut fakultas induk |
| + Prodi (di jurusan) | `POST /prodi {jurusan_id, kode, nama, jenjang, maks_sks_semester?}` | `jenjang` default `S1`; `maks_sks_semester` kosong → tidak dikirim/`null` = bawaan 24 |
| Ubah fakultas/jurusan | `PATCH /fakultas/{id}` atau `/jurusan/{id}` `{nama}` | **kode tidak bisa diubah** (input kode `disabled`) |
| Ubah prodi | `PATCH /prodi/{id} {nama, jenjang, maks_sks_semester}` | **ambil dulu `GET /prodi/{id}`** untuk mengisi batas SKS; kalau tidak, menyimpan akan mengosongkannya |
| Aktif/nonaktif | `PATCH .../{id} {aktif}` | pakai `Popconfirm` untuk menonaktifkan; kirim **hanya** `{aktif}` |

Setelah setiap aksi sukses: `await muat()` (memuat ulang pohon di `StrukturProvider`) lalu `message.success`.

### Validasi form

| Bidang | Aturan |
|---|---|
| Kode | wajib, 1–32 karakter, hanya huruf, angka, `.`, `_`, `-` (`^[A-Za-z0-9._-]+$`); unik per induk (server menolak duplikat) |
| Nama | wajib, 1–200 karakter |
| Jenjang | salah satu `D3`, `S1`, `S2`, `S3`, `Profesi` |
| Batas SKS | bilangan bulat 1–40, atau kosong. Petunjuk: "Kosong = bawaan 24. Dipakai saat memangkas rencana studi." |

### Galat server yang lazim (tampilkan apa adanya)

- 409 "Fakultas induk tidak aktif." / "Jurusan induk tidak aktif." saat mengaktifkan anak dari induk nonaktif.
- 409 "Jurusan masih memiliki N prodi aktif." / "Prodi masih memiliki N mahasiswa aktif." / "...penugasan aktif (kaprodi atau dosen PA)." saat menonaktifkan.
- 409/400 kode duplikat saat membuat.

### Kriteria selesai halaman ini

1. Pohon tampil, bisa dibuka-tutup, nonaktif ditandai.
2. Semua aksi di tabel bekerja untuk superadmin; non-superadmin tidak melihat tombol ubah.
3. Mengubah nama prodi **tidak** mengosongkan batas SKS (uji: set batas 20, ubah nama, buka lagi: masih 20).
