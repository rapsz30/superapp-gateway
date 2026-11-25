# 08. Halaman Penugasan dan DPA

## Penugasan: `/admin/penugasan`

Padanan: `components/admin/tab-penugasan.tsx`.

Penugasan = jabatan seseorang pada sebuah unit dalam rentang waktu: dekan (fakultas), kajur (jurusan), kaprodi (prodi), dosen PA (prodi atau jurusan), superadmin (global).

### Daftar

`GET /penugasan?peran=&aktif=&orang_id=&unit_id=&halaman=&ukuran=20`.

- Filter: Peran (`Select`, opsional) dan Status (`Segmented` atau `Select`: **Aktif** (bawaan, `aktif=true`), **Sudah berakhir** (`aktif=false`), **Semua** (tanpa parameter)).
- Kolom: Orang (nama lewat `useOrang`), Peran (`Tag`), Unit (`Seluruh sistem` bila `unit_tipe=global`, selain itu `"{tipe}: {namaUnit}"`), Mulai, Selesai, aksi **Akhiri**.
- Aksi **Akhiri** muncul bila belum berakhir (`selesai` kosong atau di masa depan). `Popconfirm`: "Akhiri penugasan ini mulai hari ini?" → `POST /penugasan/{id}/akhiri {selesai: null}` (null = hari ini). Penugasan yang `selesai` ≤ hari ini dianggap berakhir dan tidak boleh diakhiri lagi (server 409 "Penugasan ini sudah berakhir.").

### Tambah penugasan

Tombol header "+ Penugasan" → `Modal` dengan `Form`:

| Bidang | Perilaku |
|---|---|
| Orang | `PilihOrang` (semua peran) |
| Peran | `Select`: superadmin → semua lima peran; **non-superadmin hanya `dosen_pa`** (kaprodi hanya boleh menugaskan dosen PA di prodinya) |
| Cakupan | muncul hanya bila peran punya >1 pilihan: **`dosen_pa` → `prodi` atau `jurusan`**. Peran lain otomatis |
| Unit | `Select` unit sesuai cakupan (`global` → tidak ada; `fakultas`/`jurusan`/`prodi` → hanya yang **aktif**, label berjalur "Jurusan › Prodi") |
| Mulai | `DatePicker` opsional; kosong = hari ini |

Pasangan peran–unit yang sah (sama dengan server; UI mengaturnya agar pengguna tidak bisa memilih yang salah):

| Peran | Unit |
|---|---|
| `superadmin` | `global` |
| `dekan` | `fakultas` |
| `kajur` | `jurusan` |
| `kaprodi` | `prodi` |
| `dosen_pa` | `prodi` atau `jurusan` |

`POST /penugasan {orang_id, peran, unit_tipe, unit_id (null bila global), mulai?}`.

Keterangan peran (tampil sebagai `extra` di field Peran):
- superadmin: mengelola seluruh sistem.
- dekan: satu dekan aktif per fakultas.
- kajur: satu kajur aktif per jurusan.
- kaprodi: satu kaprodi aktif per prodi; dapat mengelola panduan dan dosen PA di prodinya.
- dosen_pa: pilih prodi (satu prodi) atau jurusan (semua prodi di jurusan itu).

Galat server yang lazim: 409 sudah ada dekan/kajur/kaprodi aktif untuk unit itu; 403 bila kaprodi mencoba peran lain. Tampilkan di `Alert` dalam modal.

---

## DPA (bimbingan): `/admin/dpa`

Padanan: `components/admin/tab-bimbingan.tsx`. (Di antarmuka disebut "DPA"; entitasnya `bimbingan`.)

Satu mahasiswa punya **satu** DPA aktif. Dosen harus punya penugasan `dosen_pa` yang mencakup prodi mahasiswa, dan **DPA harus sudah punya akun** agar pengajuan KHS bisa dikirim kepadanya. Tampilkan ini sebagai `Alert type="info"` di atas tabel.

### Daftar

`GET /bimbingan?dosen_id=&mahasiswa_id=&aktif=&halaman=&ukuran=20`.

- Filter: Dosen (`PilihOrang peran="dosen_pa"`), Status (Aktif bawaan / Sudah berakhir / Semua).
- Kolom: Mahasiswa, DPA (nama lewat `useOrang`), Mulai, Selesai (`Tag` hijau "aktif" bila kosong), aksi **Akhiri**.
- **Akhiri**: `Popconfirm` "Akhiri bimbingan ini? Pengajuan yang sedang berjalan akan tetap dengan DPA saat ini sampai ada DPA baru." → `POST /bimbingan/{id}/akhiri {}`.

### + Bimbingan

`Modal`: **Mahasiswa** (`PilihOrang peran="mahasiswa"`) dan **Dosen PA** (`PilihOrang peran="dosen_pa"`), tombol Simpan → `POST /bimbingan {dosen_id, mahasiswa_id}`.
Galat server lazim: mahasiswa tidak punya keanggotaan prodi aktif; dosen tidak punya penugasan dosen PA yang mencakup prodi mahasiswa (400, pesan jelas); mahasiswa sudah punya DPA aktif (409).
Efek samping server yang perlu diketahui: bila mahasiswa punya **pengajuan KHS berjalan**, DPA di pengajuan itu ikut dialihkan (di AlurKerja). Bila AlurKerja gagal, seluruh operasi dibatalkan dan server menjawab 502; tampilkan pesannya.

### Alihkan massal

`Modal`: **Dosen asal** dan **Dosen tujuan** (`PilihOrang peran="dosen_pa"`, harus berbeda) → konfirmasi `Modal.confirm` menyebut nama keduanya ("Alihkan SEMUA mahasiswa aktif {asal} ke {tujuan}? Pengajuan yang berjalan ikut dialihkan.") → `POST /bimbingan/pindahkan {dosen_asal_id, dosen_tujuan_id}` (tanpa `mahasiswa_ids` = semua).
Jawaban: `{ dialihkan: n, bimbingan_baru: [...] }`. Tampilkan `message.success("n mahasiswa dialihkan")`.
Atomik: bila ada satu yang gagal (mis. dosen tujuan tidak mencakup prodi seorang mahasiswa), **tidak ada yang berubah**; jelaskan itu di teks bantuan modal.

### Kriteria selesai

1. Penugasan: pilihan unit mengikuti peran/cakupan; kaprodi hanya melihat opsi `dosen_pa`.
2. DPA: buat, akhiri, alihkan massal; semua nama (bukan id) tampil di tabel.
3. Setiap galat server tampil dengan kalimat aslinya.
