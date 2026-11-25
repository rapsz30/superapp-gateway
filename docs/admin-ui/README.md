# Redesain Halaman Admin: Sidebar + Ant Design

Dokumen serah terima untuk agent atau pengembang lain. **Belum ada kode yang diubah untuk redesain ini.** Halaman admin yang ada sekarang berfungsi (lihat [01](01-keadaan-sekarang.md)); tugasnya adalah mengganti tampilannya.

## Permintaan pengguna (kutipan maksud)

> Halaman admin dijadikan **sidebar** dan pakai **Ant Design** saja. Alamat halaman admin: `/admin/beranda`.

Tangkapan layar yang dikirim pengguna menunjukkan halaman sekarang: judul "Administrasi", tab horizontal (Struktur, Orang & akun, Penugasan, DPA, Panduan, Audit), kartu putih di atas latar abu muda, tombol "+ Fakultas". Itu yang harus diganti dengan tata letak sidebar kiri + isi kanan memakai komponen Ant Design.

## Ringkasan tujuan

1. Tata letak: `Layout` Ant Design dengan `Sider` (menu kiri), header tipis, dan konten.
2. Setiap menu menjadi **rute sendiri** di bawah `/admin/...` (bukan tab dalam satu halaman).
3. Semua tampilan (tabel, form, modal, notifikasi, tanda status) memakai komponen Ant Design. CSS kustom `admin.css` dihapus.
4. **Perilaku dan API tidak berubah.** Ini murni ganti tampilan dan navigasi. Layanan `admin-service.ts` dan semua endpoint identity dipakai apa adanya.

## Urutan baca

| Berkas | Isi |
|---|---|
| [01-keadaan-sekarang.md](01-keadaan-sekarang.md) | Apa yang sudah ada, berkas mana, cara kerjanya, bug yang pernah ditemukan |
| [02-keputusan-desain.md](02-keputusan-desain.md) | Keputusan tata letak, rute, dan hal yang masih terbuka |
| [03-pemasangan-antd.md](03-pemasangan-antd.md) | Memasang Ant Design di Next 16 + React 19 + Tailwind 4 |
| [04-struktur-berkas-dan-rute.md](04-struktur-berkas-dan-rute.md) | Pohon berkas target dan peta rute |
| [05-komponen-bersama.md](05-komponen-bersama.md) | Hook yang dipertahankan, pemetaan komponen lama ke Ant Design |
| [06-beranda-dan-struktur.md](06-beranda-dan-struktur.md) | Halaman ringkasan dan struktur organisasi |
| [07-orang-dan-akun.md](07-orang-dan-akun.md) | Halaman orang, akun, keanggotaan prodi, impor CSV |
| [08-penugasan-dan-dpa.md](08-penugasan-dan-dpa.md) | Halaman penugasan jabatan dan bimbingan DPA |
| [09-panduan-dan-audit.md](09-panduan-dan-audit.md) | Halaman panduan akademik dan jejak audit |
| [10-kontrak-api.md](10-kontrak-api.md) | Semua endpoint yang dipakai, isi permintaan dan jawaban |
| [11-hak-akses.md](11-hak-akses.md) | Siapa boleh apa, dan apa yang disembunyikan di UI |
| [12-pengujian.md](12-pengujian.md) | Cara menjalankan dan menguji, jebakan yang sudah ditemui |
| [13-checklist-selesai.md](13-checklist-selesai.md) | Kriteria selesai dan larangan |

## Aturan kerja

- Semua perubahan di branch `feat/hackathon-superapp-gateway`. **Jangan commit atau push** kecuali pengguna meminta.
- Kode, nama berkas, dan teks antarmuka berbahasa Indonesia, mengikuti kode yang ada.
- Jangan mengubah layanan backend (`services/identity`). Bila API kurang, catat di [02](02-keputusan-desain.md) bagian "Terbuka" dan tanyakan pengguna.
- Jangan menyalin rahasia (`.env`, sandi, token) ke dokumen atau kode.
