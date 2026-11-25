# 07. Halaman Orang & akun: `/admin/orang`

Padanan: `components/admin/tab-orang.tsx` (komponen `TabOrang`, `FormOrang`, `FormImpor`, `DetailOrang`).

## Daftar

Panggilan: `GET /orang?q=&peran=&prodi_id=&halaman=&ukuran=20`.

Filter (di atas tabel, `Form layout="inline"` atau `Flex`):
- Cari: `Input.Search` (nama, NIM, NIDN; pencarian parsial, maks 100 karakter). Kirim saat Enter/klik.
- Peran: `Select` opsi `mahasiswa`, `dosen_pa`, `kaprodi`, `kajur`, `dekan`, `superadmin` (dan "Semua"). Server memvalidasi dengan pola `^(superadmin|dekan|kajur|kaprodi|dosen_pa|mahasiswa)$`.
- Prodi: `Select` dari `useStruktur().prodi` (termasuk nonaktif; opsi "Semua prodi").

Kolom tabel: Nama; NIM / NIDN (`—` bila kosong); Peran (`Tag color="blue"` per peran, `—` bila tidak ada); Akun (email + `Tag` status: `aktif` hijau, selain itu kuning; "belum ada akun" abu); aksi "Kelola" (membuka drawer detail).

Aksi header halaman (hanya superadmin): `Impor CSV`, `+ Orang`.

## Tambah orang (hanya superadmin)

`POST /orang { nama_lengkap, nim?, nidn?, email_kontak? }` → mengembalikan `Orang`. `Modal` + `Form`.

| Bidang | Aturan |
|---|---|
| Nama lengkap | wajib, ≤ 200 |
| NIM | opsional ≤ 32; isi untuk mahasiswa |
| NIDN | opsional ≤ 32; isi untuk dosen |
| Email kontak | opsional, format email |

Setelah sukses: muat ulang daftar dan **buka drawer orang baru** (agar admin langsung bisa membuat akun/keanggotaan).

## Impor CSV (hanya superadmin)

`POST /orang/impor` (multipart, bidang `berkas`) → `{ total, berhasil, gagal, baris: [...] }`.

- Format: UTF-8, maks 2 MB. Kolom: `nama_lengkap` (wajib), `nim`, `nidn`, `email_kontak`, `email_akun`, `prodi` (bentuk `KODE_FAKULTAS/KODE_JURUSAN/KODE_PRODI`), `angkatan`. Tampilkan format ini di `Modal` (`Typography.Paragraph` + contoh baris).
- Tiap baris diproses sendiri; satu baris gagal tidak menggagalkan yang lain.
- Laporan: `Alert` ringkasan (n berhasil, n gagal dari total) + `Table` baris: `baris` (nomor baris CSV, header = 1), `status` (`ok`/`gagal` sebagai `Tag`), `email`, `sandi_sementara`, `alasan`.
- **Sandi sementara muncul sekali di laporan ini.** Beri `Alert type="warning"` "Catat sebelum menutup" dan sediakan tombol **"Unduh laporan CSV"** (buat Blob di klien) bila ada yang punya sandi. Jangan menyimpan laporan ke `localStorage`.
- Penutupan modal dengan sandi yang belum disalin sebaiknya meminta konfirmasi.

## Drawer "Kelola" per orang

`Drawer` lebar 640 (atau halaman rinci terpisah bila dirasa lebih baik; jangan memecah rute tanpa mengubah [04](04-struktur-berkas-dan-rute.md)). Bagian dalam `Tabs` atau `Collapse`:

### 1. Data

Form (hanya superadmin; lainnya `Descriptions` baca-saja dengan catatan "Hanya superadmin yang dapat mengubah data orang."):
`PATCH /orang/{id} { nama_lengkap, nim, nidn, email_kontak }` (kosong dikirim `null`). Setelah sukses: `lupakanOrang(id)`, muat ulang daftar.

### 2. Akun

| Keadaan | Tampilan | Aksi (superadmin) |
|---|---|---|
| Sudah ada akun | email, `Tag` status, `Tag` "wajib ganti sandi" bila `wajib_ganti_sandi` | **Atur ulang sandi** (`POST /akun/{aid}/atur-ulang-sandi`, konfirmasi: "Semua sesinya akan keluar"), **Tangguhkan** / **Aktifkan** / **Nonaktifkan** (`PATCH /akun/{aid}/status {status}` dengan `aktif|ditangguhkan|nonaktif`; nonaktifkan butuh konfirmasi) |
| Belum ada akun | form: **Email akun** (wajib, email), **Sandi awal** (opsional) | **Buat akun** (`POST /akun {orang_id, email, sandi?}`) |

- Sandi kosong → server membuat sandi acak dan mengembalikannya di `sandi_sementara` (tampil sekali, lihat modal di [05](05-komponen-bersama.md)). Sandi yang diisi sendiri dicek kebijakan sandi oleh server (galat 400 dengan alasan).
- Email akun huruf kecil otomatis oleh server. Untuk **dosen**, email harus sama dengan akun AlurKerja-nya (beri `extra` petunjuk di field).
- Server menolak menonaktifkan **superadmin aktif terakhir** (409); tampilkan pesannya.
- Nilai awal field email akun: boleh diisi dari `email_kontak` (sekarang begitu).

### 3. Keanggotaan program studi (mahasiswa)

Panggilan baca: `GET /keanggotaan?orang_id={id}&ukuran=50`. Tabel: Prodi (`namaUnit`), Angkatan, Status (`Tag`; abu bila `selesai`), Mulai, Selesai.

Aksi untuk baris yang **belum selesai** (`selesai` null):

| Aksi | Panggilan | Catatan |
|---|---|---|
| Cuti | `POST /keanggotaan/{id}/status {status:'cuti'}` | tampil bila status `aktif` |
| Aktifkan | `... {status:'aktif'}` | tampil bila `cuti` |
| Lulus | `... {status:'lulus'}` | **konfirmasi**: "Bimbingan dan pengajuan yang berjalan akan dihentikan." |
| Keluar | `... {status:'keluar'}` | konfirmasi sama |
| Pindah prodi | `POST /keanggotaan/{id}/pindah {prodi_tujuan_id, angkatan?}` | **hanya superadmin**; konfirmasi sama; pilih prodi tujuan (aktif) di `Select` |

Bila orang **tidak punya** keanggotaan yang aktif: form **Daftarkan ke prodi**: `Select` prodi (aktif), `InputNumber` angkatan (1990–2100, opsional) → `POST /keanggotaan {orang_id, prodi_id, angkatan?}`. Kaprodi boleh mendaftarkan di prodinya (server mengecek cakupan).

Setelah tiap aksi sukses: muat ulang keanggotaan dan daftar orang.

## Kriteria selesai halaman ini

1. Filter dan paginasi jalan; mengganti filter kembali ke halaman 1.
2. Buat orang → akun → keanggotaan sampai terlihat di daftar tanpa muat ulang halaman.
3. Sandi sementara tampil di modal yang tidak bisa tertutup tak sengaja, dengan tombol salin.
4. Impor CSV menampilkan laporan per baris dan sandi sementara dengan peringatan.
5. Pengguna non-superadmin tidak melihat tombol yang pasti ditolak server.
