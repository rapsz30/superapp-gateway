# 06. Pengujian dan kriteria selesai

## Menjalankan

Layanan lewat Docker Compose proyek `superapp` (gateway `127.0.0.1:8080`); frontend `npx next dev -p 3001`. Bangun ulang layanan hanya bila backend berubah.

Data uji yang ada: prodi `UJI-IF`, mahasiswa `uji.mahasiswa@kampus.ac.id`, dosen sekaligus kaprodi `daffa_pa@gmail.com`. Sandi dipegang pengguna; jangan ditulis di berkas atau kode. Untuk uji tanpa menyentuh data itu, jalankan identity terhadap basis data uji dengan data tiruan seperti di `services/identity/tests/test_judul.py`.

## Skenario

1. Mahasiswa membuka halaman pengajuan, memilih satu dosen dari daftar prodinya, lalu mengirim judul.
2. Mahasiswa meminta rekomendasi; tiga kartu bertema muncul; muat ulang halaman, riwayat tetap ada.
3. Mahasiswa memilih satu kandidat, membuka halaman pengajuan, memilih pembimbing, lalu mengirim.
4. Pembimbing meminta revisi dengan catatan; mahasiswa melihat catatan, memperbaiki, mengirim.
5. Pembimbing menyetujui (coba sekali lewat web, sekali lewat Tasklist AlurKerja).
6. Halaman tema menunjukkan hitungan yang sesuai.
7. Ganti pembimbing saat pengajuan berjalan; antrean berpindah.

## Selesai bila

- [ ] `ThesisView` memakai rute identity; `judul-service.ts` tidak lagi memanggil `/api/judul-recommender`.
- [ ] Semua keadaan di [03](03-halaman-mahasiswa.md) tampil dengan data asli, bukan contoh.
- [ ] Menu kaprodi (pembimbing, tema) dan pembimbing (antrean) hanya muncul bagi yang berhak.
- [ ] Tema tampil sebagai label di semua tempat dan terekap pada grafik per prodi.
- [ ] `npx tsc --noEmit` tidak menambah galat; lebar 375 px tanpa gulir samping.
- [ ] Laporan jujur: apa yang sudah diuji di browser dan apa yang belum.
