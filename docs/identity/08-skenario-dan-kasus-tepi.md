# 08. Skenario dan Kasus Tepi

## Skenario utama

### S1. Menyiapkan kampus dari nol
1. Superadmin dibuat lewat CLI.
2. Superadmin membuat fakultas, jurusan, dan prodi.
3. Mengimpor dosen (CSV), lalu menugaskan dekan, kajur, dan kaprodi.
4. Kaprodi mengunggah panduan akademik versi 1 sebagai draf, lalu mengaktifkannya.
5. Mengimpor mahasiswa (CSV) beserta prodi dan angkatan.
6. Kaprodi menetapkan dosen PA untuk tiap mahasiswa (atau massal).

### S2. Pergantian kaprodi
1. Superadmin mengakhiri penugasan kaprodi lama pada tanggal X.
2. Membuat penugasan kaprodi baru mulai tanggal X (atau X+1).
3. Riwayat tetap ada. Token kaprodi lama kehilangan hak paling lama 15 menit kemudian.

### S3. Dosen PA berhenti atau cuti
1. Kaprodi memakai `/bimbingan/pindahkan` untuk mengalihkan seluruh mahasiswa ke PA lain.
2. Penugasan `dosen_pa` lama diakhiri.
3. Jika ada pengajuan yang menunggu persetujuan PA lama, pemrosesnya harus dialihkan juga (lihat integrasi dengan StudentGateway).

### S4. Panduan akademik diperbarui
1. Kaprodi mengunggah versi 2 sebagai draf.
2. Setelah diperiksa, mengaktifkan versi 2. Versi 1 menjadi `diarsipkan`.
3. Pengajuan yang sudah berjalan tetap merujuk versi 1 (disimpan `panduan_id` pada pengajuan di layanan konsumen).

### S5. Mahasiswa pindah prodi
1. Superadmin memakai `/keanggotaan/{id}/pindah`.
2. Keanggotaan lama berstatus `pindah`, yang baru `aktif`.
3. Bimbingan lama diakhiri; PA baru ditetapkan oleh kaprodi tujuan.

### S6. Dosen merangkap
Dosen yang juga kaprodi punya dua penugasan aktif. Token memuat `roles: ["dosen_pa","kaprodi"]` dan dua `scopes`. Ia melihat mahasiswa bimbingannya dan seluruh prodinya.

## Kasus tepi

| Kasus | Perilaku yang diharapkan |
|---|---|
| Menutup prodi yang masih punya mahasiswa aktif | 409, sebutkan jumlah mahasiswa |
| Menutup jurusan yang masih punya prodi aktif | 409 |
| Menugaskan kaprodi kedua di prodi yang sama | 409 dari indeks unik |
| Dosen PA ditugaskan ke prodi yang tidak aktif | 400 |
| Mahasiswa tanpa PA aktif | sah, tetapi muncul di laporan "belum punya PA" |
| Mengaktifkan panduan yang berstatus diarsipkan | diperbolehkan, versi aktif saat ini diarsipkan; tercatat di audit |
| Dua admin mengaktifkan panduan bersamaan | salah satu menang, yang lain 409 (transaksi + indeks unik) |
| Email sama dengan beda huruf | ditolak (indeks pada `lower(email)`) |
| NIM sudah dipakai | 409 pada impor, baris dilaporkan, baris lain tetap diproses |
| Impor CSV dengan 500 baris, 3 gagal | 497 berhasil, laporan memuat nomor baris dan alasan gagal |
| Penugasan tanggal mulai di masa depan | tidak aktif sampai tanggalnya, tidak masuk token |
| Akun ditangguhkan | login ditolak; refresh token dicabut; access token mati paling lama 15 menit |
| Superadmin terakhir ditangguhkan atau diakhiri | ditolak, harus ada minimal satu superadmin aktif |
| Orang tanpa akun (belum pernah login) | boleh ada di struktur dan bimbingan |
| Zona waktu | tanggal penugasan memakai WIB (Asia/Jakarta); disimpan sebagai `date` |
| Perubahan peran saat sesi berjalan | berlaku setelah token disegarkan |
| Ukuran token | superadmin memakai cakupan `global`, bukan daftar semua unit |

## Hal yang sengaja tidak ada

- Hapus fisik unit, orang, atau penugasan. Semua lewat penutupan agar riwayat utuh.
- Pendaftaran akun mandiri.
- Pengubahan riwayat audit.
