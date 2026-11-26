# 04. Kaprodi dan pembimbing (Ruang dosen)

Tambahkan menu di `components/dosen/dosen-shell.tsx`.

## Kaprodi: "Pembimbing TA" (`/dosen/pembimbing-ta`)

- Pilih prodi (bila lebih dari satu).
- Tabel mahasiswa: nama, NIM, pembimbing (atau tag "Belum ditunjuk"), judul terakhir + tema + status.
- Aksi **Tunjuk / Ganti**: pilih dosen dari `GET /pembimbing-ta/dosen`, `PUT /pembimbing-ta`.
- Bila mahasiswa punya pengajuan berjalan, ingatkan di konfirmasi bahwa tinjauan ikut pindah ke dosen baru.
- Saring "belum punya pembimbing" (boleh di sisi klien).

## Pembimbing: "Judul perlu ditinjau" (`/dosen/judul`)

Pembimbing bisa dosen PA atau kaprodi; tampilkan menu untuk keduanya.

- Antrean: `?pembimbing_id=<saya>&status=diajukan`, `tahap === 'tinjau'`; tampilkan NIM, nama, tema, judul, lama menunggu.
- Tab riwayat: semua pengajuan bimbingan saya (disetujui, dibatalkan, menunggu perbaikan).
- Detail: judul, tema, topik minat, deskripsi, metodologi per baris, kata kunci, referensi, revisi ke berapa, catatan sebelumnya.
- **Setujui** (dengan konfirmasi) dan **Minta revisi** (catatan wajib). Contoh pola: `components/dosen/detail-pengajuan.tsx`.
- 409 berarti keputusan sudah dibuat di Tasklist: tampilkan pesan lalu muat ulang.
