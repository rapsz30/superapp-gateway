# Serah terima tampilan: judul tugas akhir

> **Diperbarui 26 Nov 2026:** halaman mahasiswa `/judul/rekomendasi` kini berupa brainstorm dan kandidat (`frontend/components/judul/brainstorm.tsx`). Alur dan rutenya di [14](../identity/14-pengajuan-judul-ta.md#brainstorm-sebelum-memilih-migrasi-0006); bagian lama tentang rekomendasi langsung tidak berlaku untuk halaman itu.

Backend **sudah jadi dan teruji**. Tugas agent penerima: tampilan web di `frontend/`. Jangan mengubah `services/` tanpa membicarakannya dulu.

| Berkas | Isi |
|---|---|
| [01-alur-dan-aturan.md](01-alur-dan-aturan.md) | siapa melakukan apa, status, aturan yang harus tampak di layar |
| [02-kontrak-api.md](02-kontrak-api.md) | semua rute, bentuk data, dan galat |
| [03-halaman-mahasiswa.md](03-halaman-mahasiswa.md) | menu Judul Tugas Akhir |
| [04-halaman-kaprodi-dan-dosen.md](04-halaman-kaprodi-dan-dosen.md) | penunjukan pembimbing dan tinjauan di Ruang dosen |
| [05-visualisasi-tema.md](05-visualisasi-tema.md) | rekap tema terbanyak per prodi |
| [06-pengujian-dan-selesai.md](06-pengujian-dan-selesai.md) | cara menguji dan kriteria selesai |

## Yang sudah ada di frontend

| Berkas | Catatan |
|---|---|
| `app/beranda/page.tsx` → `ThesisView`, `ThesisResults` | tampilan chat minat dan kartu hasil; **masih memakai rute lama** |
| `src/services/judul-service.ts` | memanggil `/api/judul-recommender/get-recommendations`; harus diganti ke identity |
| `components/course-dashboard.tsx`, `components/submit-card.tsx` | pola dasbor, status, dan riwayat milik mata kuliah; ikuti gayanya |
| `components/dosen/dosen-shell.tsx` | menu Ruang dosen (`PEMBIMBING`, `KAPRODI`) |
| `components/dosen/bersama.tsx` | `useMuat` (muat + segarkan berkala), `waktu` |
| `components/dosen/halaman-analitik.tsx` | contoh grafik batang dengan recharts |
| `src/lib/api.ts` | `apiFetch`, `errorMessage` |

## Aturan kerja

- Branch `feat/hackathon-superapp-gateway`. Jangan commit atau push tanpa diminta.
- Ada perubahan belum di-commit dari beberapa sesi; **jangan mengembalikan** perubahan yang bukan milikmu.
- Halaman mahasiswa memakai CSS sendiri (`app/globals.css`); Ruang dosen memakai Ant Design 6 (`Alert` memakai `title`).
- `next.config` mengabaikan galat tipe saat build, jadi jalankan `npx tsc --noEmit` (ada 5 galat lama di `components/admin/admin-dashboard.tsx`).
- Server dev pengguna berjalan di port 3001.
