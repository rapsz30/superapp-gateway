# 01. Keputusan dan Asumsi

## Keputusan (dari pemilik proyek)

| # | Keputusan | Dampak |
|---|---|---|
| K1 | Urutan hierarki Fakultas → Jurusan → Prodi | Prodi menunjuk ke jurusan, jurusan ke fakultas |
| K2 | Panduan akademik per prodi, bisa diperbarui | Perlu versi dan penanda versi aktif |
| K3 | Sumber akun dibuat baru | Layanan `identity` baru, bukan memperluas Micro-cred |
| K4 | Akun lama diberi komentar tidak dipakai | Tidak ada data dihapus, tidak ada migrasi paksa |
| K5 | Struktur organisasi di Postgres | Satu database `identity-db`, migrasi dengan Alembic |
| K6 | Skema PocketBase tidak diekspor | Tabel baru dimulai dari nol, tanpa impor data panduan lama |
| K7 | Superadmin mengatur seluruh struktur | Ada peran `superadmin` di level global |

## Asumsi (belum dikonfirmasi, mudah diubah)

| # | Asumsi | Jika salah |
|---|---|---|
| A1 | Satu jurusan boleh punya banyak prodi | Sudah didukung. Jika selalu satu, tetap aman |
| A2 | Satu prodi hanya di satu jurusan | Jika prodi lintas jurusan, perlu tabel relasi banyak ke banyak |
| A3 | Satu mahasiswa hanya di satu prodi pada satu waktu | Pindah prodi dicatat sebagai riwayat, bukan dua prodi aktif |
| A4 | Satu mahasiswa punya tepat satu dosen PA aktif | Jika boleh dua PA, ubah indeks unik |
| A5 | Satu dosen PA boleh membimbing mahasiswa dari lebih dari satu prodi | Jika dibatasi, tambah pemeriksaan |
| A6 | Satu orang boleh merangkap beberapa peran (dosen sekaligus kaprodi) | Karena itu orang dipisah dari penugasan |
| A7 | Dekan ada walau tidak disebut pemilik proyek | Bisa dibuang tanpa mengubah desain lain |
| A8 | Panduan lama dari PocketBase tidak perlu dipindahkan | Jika perlu, buat skrip impor terpisah |

## Di luar cakupan tahap ini

- Memindahkan `matkul`, `judul`, dan Micro-cred agar memakai akun baru. Itu tahap lanjutan.
- Single sign-on dengan sistem kampus (SIAKAD, LDAP). Disiapkan titik masuknya, belum dibuat.
- Pencabutan token seketika (daftar cabut). Lihat [05](05-alur-auth-dan-token.md).
- Antarmuka superadmin. Tahap ini hanya API.
