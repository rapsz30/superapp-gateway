# Hasil Uji Alur Nyata (E2E) lewat Gateway

Dijalankan 2026-10-27 dengan `gateway/tests/e2e-flow.ps1 -Cycles 5` terhadap stack mode debug (semua service healthy), semua panggilan lewat `http://127.0.0.1:8080` dengan token JWT. Tidak ada token, email, atau jawaban peserta di dokumen ini.

> [!WARNING]
> **Waktu Alur A tidak mewakili skoring LLM yang sebenarnya.** Selama uji, OpenAI menjawab `You have no credits remaining` untuk semua 15 esai (3 esai × 5 siklus). Skor esai memakai fallback, dan setiap esai menghabiskan 3 percobaan ulang. Rekomendasi juga berasal dari fallback RAG (lihat bagian temuan). Isi ulang kredit OpenAI lalu jalankan ulang skrip sebelum angka waktu dipakai untuk evaluasi.

## Ringkasan

| Alur | Hasil |
|---|---|
| A. Micro-cred (5 siklus) | 5/5 selesai (`completed`). Waktu submit sampai selesai: min 19,10 s, median 19,81 s, maks 25,82 s. Tapi lihat peringatan di atas. |
| B. Judul (5 siklus) | 4/5 sukses (HTTP 200). Waktu (hanya 200): min 6,28 s, median 7,10 s, maks 8,13 s. 1 kegagalan 500 dari Groq. |
| C-1. Overhead health | Median 11,5 ms lewat gateway vs 10,6 ms langsung, selisih sekitar 1,0 ms (10 request tiap sisi). |
| C-2. `rt - urt` di log nginx | Alur A: median 2,0 ms (n=66, maks 37 ms). Alur B: median 3,0 ms (n=5, maks 8 ms). |

Pembanding dari paper: median 13,21 s. Median Alur A di uji ini 19,81 s, tetapi kondisinya tidak sebanding (percobaan ulang ke layanan yang kehabisan kredit dan fallback RAG), sehingga angka itu belum bisa dibandingkan langsung dengan 13,21 s.

## Metode

- Satu akun baru per siklus (register lalu login), role `backend-engineer`. Body `start` dan `submit` disusun dari skema `/openapi.json` dan bentuk soal pada respons `start`: soal `theoretical` memilih salah satu opsi, soal `essay` diisi 2 sampai 4 kalimat yang relevan, soal `profile` mengikuti `metadata.captures` dan `metadata.accepted_values`.
- Alur A: waktu diukur klien (stopwatch) dari sebelum `POST submit` sampai `GET status` mengembalikan `completed`, dengan polling tiap 2 detik (maks 120 detik). Granularitas sekitar 2 detik. `email-summary` dan webhook tidak dipanggil.
- Alur B: satu `POST /api/judul-recommender/get-recommendations` per siklus dengan token student, waktu dari `curl -w %{time_total}`. Kegagalan tidak di-retry.
- Alur C-1: 10 `GET` health lewat `/api/micro-cred/health` dan langsung ke `127.0.0.1:8000/health`, diselang-seling. Rute health publik, jadi tidak melewati verifikasi token. Alur C-2: selisih `rt` dikurangi `urt` dari log akses nginx sejak skrip mulai. Selisih ini mencakup verifikasi `auth_request`, pembacaan body klien, dan overhead proxy.

## Alur A: Micro-cred

| Siklus | Register | Login | Start | Submit | Status akhir | Waktu (s) | Rekomendasi | Dengan `match_reason` | Ringkasan |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 201 | 200 | 200 | 200 | completed | 25,82 | 10 | 10 | ada |
| 2 | 201 | 200 | 200 | 200 | completed | 24,94 | 10 | 10 | ada |
| 3 | 201 | 200 | 200 | 200 | completed | 19,10 | 10 | 10 | ada |
| 4 | 201 | 200 | 200 | 200 | completed | 19,81 | 10 | 10 | ada |
| 5 | 201 | 200 | 200 | 200 | completed | 19,48 | 6 | 6 | ada |

Semua `GET result` mengembalikan 200. Setiap rekomendasi memuat penjelasan (`match_reason`).

Catatan: `processing_duration_ms` pada hasil hanya 20 sampai 83 ms, jauh di bawah waktu yang diukur klien (sekitar 20 detik). Field itu tampaknya tidak mencakup seluruh pipeline (kemungkinan hanya tahap tertentu), sehingga tidak dipakai sebagai waktu pemrosesan.

## Alur B: Judul

| Siklus | HTTP | Waktu (s) | Rekomendasi | Referensi per rekomendasi |
|---|---|---|---|---|
| 1 | 500 | 8,76 | 0 | - |
| 2 | 200 | 6,28 | 3 | 2, 2, 2 |
| 3 | 200 | 7,36 | 2 | 2, 2 |
| 4 | 200 | 6,83 | 2 | 2, 2 |
| 5 | 200 | 8,13 | 3 | 2, 2, 2 |

Tingkat sukses 4/5. Jumlah rekomendasi bervariasi (2 sampai 3).

## Temuan dari log

Dihitung dari log `microcred-api` sejak skrip mulai (satu kali uji, 5 siklus):

| Event | Jumlah |
|---|---|
| `gpt_rate_limited` (alasan: `no credits remaining`) | 45 (3 percobaan × 15 esai) |
| `essay_scoring_failed` | 15 |
| `essay_scoring_fallback_used` | 15 |
| `essay_scoring_completed` | 5 |
| `rag_no_matches` dan `rag_fallback_activated` | 5 dan 5 |
| `fusion_completed` | 5 |
| `degraded: true` pada ringkasan skor | 0 (5 bernilai false) |

- Semua skoring esai gagal karena kredit OpenAI habis, tetapi assessment tetap berstatus `completed` dan tidak ditandai `degraded`. Kegagalan itu tidak terlihat dari respons API.
- Pipeline GPT, RAG, dan fusion berjalan di dalam proses `microcred-api` karena `AUTO_PROCESS_JOBS=true` (`assessments.py` memanggil `process_assessment_jobs`), bukan di `microcred-worker`.
- **Log worker:** selama uji, `microcred-worker` tidak mencatat eksekusi job apa pun (0 baris `score_essay`, 0 baris `generate_recommendations`, 0 baris error). Worker hanya mencatat start-up (`jobs=['score_essay', 'generate_recommendations']`) dan pembersihan registry berkala. Jadi job tersebut tidak tercatat sukses di worker karena memang tidak dijalankan di sana pada konfigurasi ini.

## Kegagalan

| Alur | Kegagalan | Penyebab yang diketahui |
|---|---|---|
| B siklus 1 | HTTP 500 `Terjadi kesalahan internal: Error code: 400 ... Failed to generate JSON` | Groq gagal menghasilkan JSON valid (masalah model Groq yang sudah diketahui). Tidak di-retry. |
| A (semua siklus) | Skoring esai gagal 15/15, tidak tampak di respons | Kredit OpenAI habis. Pipeline memakai fallback dan tetap `completed`. |
| A (semua siklus) | RAG tanpa kecocokan (`rag_no_matches`), memakai fallback | Belum diselidiki. |
| A siklus 5 | Hanya 6 rekomendasi (siklus lain 10) | Penyebab belum diketahui. |

## Keterbatasan

- Satu mesin, satu klien, berurutan. Ini bukan uji beban dan tidak mengukur konkurensi.
- Hanya 5 siklus per alur, jadi min, median, dan maks belum cukup untuk kesimpulan statistik.
- Waktu Alur A terkontaminasi percobaan ulang ke OpenAI yang kehabisan kredit (lihat peringatan).
- Polling status tiap 2 detik membuat waktu Alur A bergranularitas sekitar 2 detik.
- `rt - urt` mencakup verifikasi token dan pembacaan body, bukan hanya overhead proxy. C-1 mengukur rute publik tanpa verifikasi.
- Port debug 8000 harus aktif untuk C-1 (mode `docker compose up -d`).

## Menjalankan ulang

```powershell
powershell -File gateway\tests\e2e-flow.ps1 -Cycles 5 -OutJson hasil.json
```

Skrip memanggil layanan LLM berbayar (maksimal 5 siklus per alur disarankan), membutuhkan stack berjalan, dan memanggil `docker compose logs` untuk C-2 dan log worker.

