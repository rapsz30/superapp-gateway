# 10. Pertanyaan Terbuka

Yang paling memengaruhi skema ada di bagian atas. Jawab sebelum tahap 1 dimulai.

## Memengaruhi skema

| # | Pertanyaan | Asumsi sekarang |
|---|---|---|
| Q1 | Apakah satu prodi bisa berada di lebih dari satu jurusan? | tidak |
| Q2 | Apakah satu mahasiswa boleh punya lebih dari satu dosen PA pada saat yang sama? | tidak, tepat satu |
| Q3 | Apakah satu dosen PA boleh membimbing mahasiswa dari prodi berbeda? | ya |
| Q4 | Apakah ada jabatan lain yang perlu masuk (sekretaris jurusan, wakil dekan, koordinator, tata usaha)? | tidak |
| Q5 | Apakah panduan akademik dibedakan per angkatan di dalam satu prodi, selain per versi? | tidak; satu versi aktif berlaku untuk semua |
| Q6 | Apakah matkul dan kurikulum juga akan dikelola di layanan ini? | tidak; tetap di layanan matkul |

## Memengaruhi hak akses

| # | Pertanyaan | Asumsi sekarang |
|---|---|---|
| Q7 | Apakah kaprodi boleh menugaskan dosen PA sendiri, atau hanya superadmin? | kaprodi boleh untuk prodinya |
| Q8 | Apakah dekan dan kajur hanya melihat, tanpa hak ubah? | ya, hanya baca |
| Q9 | Apakah perlu admin tingkat fakultas (operator) di bawah superadmin? | tidak |
| Q10 | Apakah mahasiswa boleh melihat nama dosen PA dan kaprodinya? | ya |

## Memengaruhi operasional

| # | Pertanyaan | Asumsi sekarang |
|---|---|---|
| Q11 | Dari mana data awal dosen dan mahasiswa? | CSV dari bagian akademik |
| Q12 | Apakah perlu SSO dengan sistem kampus? | tidak untuk tahap ini |
| Q13 | Bagaimana alur lupa sandi? | superadmin mengatur ulang; email menyusul |
| Q14 | Berapa lama riwayat audit disimpan? | tanpa batas |
| Q15 | Berapa kira-kira jumlah mahasiswa dan dosen? | ribuan; tidak perlu optimasi khusus |
| Q16 | Panduan akademik yang sudah ada di PocketBase perlu dipindah? | tidak |

## Memengaruhi tahap lanjutan

| # | Pertanyaan | Asumsi sekarang |
|---|---|---|
| Q17 | Kapan layanan lain dipindah ke akun baru? | setelah identity stabil |
| Q18 | Apakah StudentGateway (proyek `program`) akan memakai struktur dan dosen PA dari sini? | ya, sebagai tahap lanjutan |
| Q19 | Apakah NIM boleh dikirim ke AlurKerja sebagai identitas mahasiswa? | sudah diputuskan di StudentGateway; berlaku sama |

## Integrasi matkul dan pengajuan (baru)

| # | Pertanyaan | Asumsi sekarang |
|---|---|---|
| Q20 | Frontend dipindah login ke identity? | **sudah dipindah** (dokumen 11). Konsekuensi: Micro-Credential berhenti untuk akun baru |
| Q21 | Di mana status pengajuan ke DPA disimpan? | **di identity** (tabel `pengajuan`); hasil langkah AI di matkul. Lihat [12](12-pengajuan-ke-dpa.md) dan [13](13-proses-alurkerja-penuh.md) |
| Q22 | Langkah "unggah panduan" di frontend | **dihapus**; prodi tanpa panduan aktif menampilkan pesan untuk menghubungi kaprodi |

## Cara menjawab

Cukup balas dengan nomor dan jawabannya, misalnya "Q2: boleh dua PA". Dokumen terkait akan diperbarui dan asumsi di [01](01-keputusan-dan-asumsi.md) dicoret.
