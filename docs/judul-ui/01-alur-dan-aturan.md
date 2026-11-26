# 01. Alur dan aturan

## Peran

| Peran | Melakukan |
|---|---|
| Mahasiswa | meminta rekomendasi, memilih atau menyunting judul, memilih dosen pembimbing dari daftar prodi, mengajukan, memperbaiki, membatalkan |
| Kaprodi (atau superadmin) | mengelola penugasan pembimbing awal; melihat pengajuan dan rekap tema prodinya |
| Pembimbing TA | menyetujui atau meminta revisi (di web **atau** Tasklist AlurKerja) |
| Kajur, dekan | melihat rekap tema sesuai cakupan |

Pembimbing TA **bukan** otomatis dosen PA. Mahasiswa memilih dosen yang punya penugasan Dosen PA di prodinya atau kaprodi prodi tersebut, dengan akun aktif. Bila kaprodi sudah menetapkan pembimbing awal, pilihan itu menjadi pilihan pertama pada form.

## Keadaan pengajuan

| `status` | `tahap` | Label yang disarankan | Aksi mahasiswa | Aksi pembimbing |
|---|---|---|---|---|
| `diajukan` | `tinjau` | Menunggu pembimbing | Batalkan | Setuju / Minta revisi |
| `diajukan` | `perbaikan` | Perlu Anda perbaiki | Perbaiki dan kirim, Batalkan | menunggu |
| `disetujui` | `selesai` | Disetujui | — | — |
| `dibatalkan` | apa pun | Dibatalkan | Ajukan lagi | — |

## Aturan yang harus tampak di layar

- Tanpa pembimbing TA, mahasiswa **tetap bisa meminta rekomendasi**, tetapi tombol ajukan dinonaktifkan dengan keterangan "Hubungi kaprodi".
- Hanya satu pengajuan `diajukan` per mahasiswa.
- Catatan wajib saat meminta revisi.
- Setiap judul punya **satu tema** dari daftar baku. Tampilkan sebagai label di kartu rekomendasi, form, detail, dan daftar.
- Keputusan lewat Tasklist terbaca saat data dimuat; segarkan berkala (5–20 detik) selama `status = diajukan`.
- Jangan menjanjikan referensi pasti relevan; tautan cadangan berupa pencarian Google Scholar bisa muncul.
