# 09. Halaman Panduan akademik dan Jejak audit

## Panduan: `/admin/panduan`

Padanan: `components/admin/tab-panduan.tsx`.

Setiap prodi punya satu panduan **aktif**. Rekomendasi mata kuliah dan pemeriksaan KHS memakai panduan aktif itu. Unggahan baru berstatus **draf** sampai diaktifkan; versi lama otomatis menjadi **diarsipkan** dan tidak pernah dihapus. Pengajuan KHS yang sedang berjalan tetap memakai versi yang dipakai saat ekstraksi.

### Pemilih prodi

Di atas halaman: `Select showSearch` prodi aktif (dari `useStruktur().prodi`). Sebelum dipilih, tampilkan `Empty` "Pilih program studi untuk melihat panduannya." Boleh menyimpan pilihan di query string (`?prodi=<id>`) supaya tautan bisa dibagikan.

### Riwayat versi

`GET /prodi/{id}/panduan` → `{data: Panduan[], total}` (urut versi menurun; tanpa paginasi).

`Panduan`: `{ id, prodi_id, versi, judul, berlaku_mulai, status: 'draf'|'aktif'|'diarsipkan', berkas_nama, teks_karakter }`.

Kolom: Versi (`v{n}`), Judul + nama berkas (teks sekunder), Status (`Tag`: aktif hijau, draf kuning, diarsipkan abu), Berlaku (tanggal atau `—`), Teks terbaca (`{n} karakter`, id-ID, atau `—`), aksi.

Aksi per baris:
- **Buka PDF**: berkas butuh token, jadi **jangan** pakai `<a href>` langsung. Panggil `adminService.unduhPanduan(id)` (mengembalikan `Blob`), buat `URL.createObjectURL`, `window.open(url, '_blank', 'noopener')`, cabut URL setelah ± 60 detik.
- **Aktifkan** (selain yang sudah aktif): `Popconfirm`/`Modal.confirm`. Teks: bila ada versi aktif lain → "Aktifkan versi {n}? Versi {m} akan diarsipkan. Pengajuan yang sudah berjalan tetap memakai versi lamanya."; bila tidak ada → "Aktifkan versi {n}?". → `POST /panduan/{id}/aktifkan` lalu muat ulang.

Bila prodi belum punya panduan: `Alert type="warning"` "Belum ada panduan untuk prodi ini. Pengajuan KHS belum dapat dilakukan sebelum ada panduan aktif." (server menjawab 409 pada pengajuan tanpa panduan aktif).

### Unggah versi baru

`Card`/`Modal` dengan `Form`:

| Bidang | Aturan |
|---|---|
| Judul | wajib, ≤ 300 karakter (mis. "Panduan Akademik Informatika 2024/2025") |
| Berlaku mulai | `DatePicker` opsional |
| Berkas PDF | wajib; `Upload` dengan `beforeUpload={() => false}`, `accept=".pdf,application/pdf"`, `maxCount={1}`; **harus PDF berteks (bukan hasil pindai)**, maks 20 MB |

`adminService.unggahPanduan(prodiId, judul, berkas, berlakuMulai?)` (multipart; **kirim lewat service ini**, jangan `Upload action=`). Hasil: status `draf`. Setelah sukses: `message.success("Panduan diunggah sebagai draf. Aktifkan agar dipakai.")`, kosongkan form (reset `Upload`), muat ulang riwayat.

Validasi klien yang membantu (server tetap memvalidasi): ukuran ≤ 20 MB, ekstensi `.pdf`. Galat server: 413 terlalu besar; 400 bukan PDF (diperiksa dari isi, bukan nama); 422 PDF tidak bisa dibaca teksnya (kemungkinan hasil pindai); 409 prodi nonaktif.

### Hak akses

Superadmin: semua prodi. Kaprodi: hanya prodinya (server menolak dengan 403 bila di luar cakupan; UI cukup menampilkan pesannya, atau membatasi pilihan prodi bila ada cara memperoleh cakupan, lihat [11](11-hak-akses.md)).

### Kriteria selesai

1. Unggah PDF → muncul sebagai draf → aktifkan → status menjadi aktif, versi lama menjadi diarsipkan.
2. "Buka PDF" membuka berkas di tab baru (membuktikan unduhan ber-token bekerja).
3. File non-PDF dan > 20 MB ditolak dengan pesan yang jelas.

---

## Jejak audit: `/admin/audit` (khusus superadmin)

Padanan: `components/admin/tab-audit.tsx`.

Semua perubahan data tercatat dan **tidak dapat diubah atau dihapus** (trigger database). Halaman ini hanya membaca.

### Daftar

`GET /audit?aksi=&pelaku_id=&objek_id=&dari=&sampai=&halaman=&ukuran=30` (urut terbaru dulu).

Entri: `{ id, pelaku_id, aksi, objek_tipe, objek_id, sebelum, sesudah, waktu }`.

Filter: **Aksi** (cocok persis; `AutoComplete` dengan contoh (daftar **tidak lengkap**; nama aksi diambil dari kode `audit.catat(...)` di `services/identity/src/api/routes/*.py`, verifikasi dengan `grep -rn "audit.catat" services/identity/src` sebelum memakainya sebagai saran; nilai bebas diketik tetap harus diterima) `panduan.aktifkan`, `panduan.unggah`, `panduan.arsipkan`, `akun.buat`, `akun.atur_ulang_sandi`, `bimbingan.buat`, `bimbingan.akhiri`, `orang.buat`, `orang.ubah`, `keanggotaan.buat`, `penugasan.buat`, `prodi.ubah`, `jurusan.ubah`, `fakultas.ubah`, `akun.buat_superadmin`), **Rentang waktu** (`DatePicker.RangePicker` → `dari`/`sampai` ISO), opsional Pelaku (`PilihOrang`).

Kolom: Waktu (`toLocaleString('id-ID')`), Pelaku (nama lewat `useOrang`; `pelaku_id` null → teks "sistem"), Aksi (`Typography.Text code`), Objek (`objek_tipe`), baris dapat diperluas (`expandable`) untuk **Sebelum**/**Sesudah**: dua `Typography.Paragraph` berisi JSON terformat (`<pre>` atau `Descriptions`), tinggi maksimum ± 260 px dengan scroll.

### Catatan keamanan

- Server **sudah membuang** kolom rahasia dari audit (`sandi_hash`, `token_hash`, `teks` panduan). Jangan menambahkan penampilan data mentah lain.
- Jangan menyediakan tombol hapus/ubah.

### Kriteria selesai

1. Filter aksi dan rentang waktu bekerja; paginasi server.
2. Baris bisa diperluas menampilkan sebelum/sesudah.
3. Non-superadmin yang membuka URL langsung melihat 403 di dalam shell.
