# 03. Halaman mahasiswa (menu Judul Tugas Akhir)

Ikuti pola Mata Kuliah: **dasbor dulu**, baru form. Pengguna sudah meminta ini untuk Mata Kuliah.

## A. Dasbor (`GET /judul/saya`)

1. Kepala: nama pembimbing TA, atau "Belum ditunjuk. Hubungi kaprodi."
2. Kartu status pengajuan (bila ada dan tidak dibatalkan): badge, judul, tema, catatan pembimbing, jumlah revisi; tombol sesuai tabel di [01](01-alur-dan-aturan.md).
3. Tombol utama **Cari ide judul** → bagian B.
4. Riwayat rekomendasi: topik, tanggal, buka kembali tiga judulnya (tanpa memanggil AI lagi).

## B. Rekomendasi

- Pakai tampilan chat yang ada (`ThesisView`), ganti pemanggilan ke `POST /judul/rekomendasi` dengan `{ minat }`.
- Tampilkan proses (sampai ±40 detik); tombol kirim nonaktif selama berjalan.
- Bila `memakai_nilai`, beri keterangan "Disesuaikan dengan nilai KHS Anda".
- Kartu hasil: judul, **label tema**, deskripsi, metodologi (pecah per baris), kata kunci, referensi (tautan baru, `rel="noopener noreferrer"`).
- Setiap kartu: tombol **Pilih judul ini** → bagian C.
- Tombol "Ajukan judul sendiri" membuka form kosong.

## C. Form pengajuan

| Field | Catatan |
|---|---|
| Judul | 10–300 karakter |
| Tema | pilihan dari `GET /judul/tema`; terisi dari kartu, boleh diganti |
| Deskripsi | 20–2000 |
| Metodologi | opsional |
| Kata kunci, referensi | terbawa dari kartu; boleh dihapus |
| `topik` | isi dengan minat yang diketik, bila ada |

- Konfirmasi sebelum kirim, sebut nama pembimbing.
- `POST /pengajuan-judul`; untuk perbaikan `PUT /pengajuan-judul/{id}` dengan form terisi data lama dan **catatan pembimbing tampil di atas form**.
- Tampilkan `detail` dari galat 409/422/502 apa adanya (sudah berbahasa Indonesia, kecuali 422).

## Keadaan yang wajib ada

memuat, gagal memuat (dengan "Coba lagi"), belum punya pembimbing, belum pernah mengajukan, menunggu, perlu perbaikan, disetujui (tampilkan judul final yang mudah dibaca), dibatalkan. Lebar ponsel 375 px tanpa gulir samping.
