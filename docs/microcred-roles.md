# Matriks Peran Micro-cred

Hasil audit baca-saja terhadap `services/microcred/src/api/routes/*.py` dan `src/api/deps.py`. Tidak ada kode yang diubah untuk dokumen ini.

## Tabel endpoint

| Method | Path | Token wajib | Role yang diizinkan | Catatan |
|---|---|---|---|---|
| GET | `/health` | Tidak | Publik | Probe observabilitas |
| POST | `/auth/register` | Tidak | Publik | Klien memilih `role` (student atau advisor). `admin` ditolak 403 |
| POST | `/auth/login` | Tidak | Publik | |
| GET | `/auth/me` | Ya | Semua role (`get_current_user`) | Profil diambil dari database |
| POST | `/auth/change-password` | Ya | Semua role (`get_current_user`) | |
| GET | `/tracks` | Tidak | Publik | |
| GET | `/tracks/{slug}` | Tidak | Publik | |
| POST | `/tracks` | Ya | admin | |
| PATCH | `/tracks/{slug}` | Ya | admin | |
| DELETE | `/tracks/{slug}` | Ya | admin | |
| GET | `/questions` | Tidak | Publik | |
| GET | `/questions/{question_id}` | Tidak | Publik | |
| POST | `/questions` | Ya | admin | |
| PATCH | `/questions/{question_id}` | Ya | admin | |
| DELETE | `/questions/{question_id}` | Ya | admin | |
| POST | `/assessments/start` | Ya | student, admin | |
| DELETE | `/assessments/{assessment_id}/abandon` | Ya | student, admin | |
| GET | `/assessments/stats/user` | Ya | student, admin | |
| POST | `/assessments/{assessment_id}/submit` | Ya | student, admin | |
| GET | `/assessments/{assessment_id}/status` | Ya | student, admin | |
| POST | `/assessments/{assessment_id}/webhook` | Ya | student, admin | |
| GET | `/assessments/{assessment_id}/result` | Ya | student, admin | |
| POST | `/assessments/{assessment_id}/email-summary` | Ya | student, admin | |
| POST | `/assessments/{assessment_id}/feedback` | Ya | student, advisor, admin | |

## Ringkasan per role

- **student**: mengikuti assessment (mulai, kirim, lihat status dan hasil, batalkan, statistik, webhook, email ringkasan), memberi feedback, melihat profil dan mengganti password sendiri.
- **advisor**: hanya endpoint feedback assessment, ditambah `/auth/me` dan `/auth/change-password`. Tidak bisa memulai atau melihat hasil assessment.
- **admin**: semua yang bisa dilakukan student, ditambah menulis (POST, PATCH, DELETE) pada tracks dan questions.

## Endpoint tanpa proteksi

`/health`, `/auth/register`, `/auth/login`, `GET /tracks`, `GET /tracks/{slug}`, `GET /questions`, `GET /questions/{question_id}`.

Tidak ada endpoint tulis pada tracks atau questions yang bisa dipanggil student atau tanpa token: semuanya memakai `require_roles(["admin"])`.

## Catatan temuan

- Role disimpan di kolom `users.role` (enum `student|advisor|admin`). Saat login atau registrasi, `AuthService._generate_tokens` memasukkan `roles=[user.role.value]` ke token. `get_current_user` hanya membaca claim token (`sub`, `roles`, `email`) tanpa membaca database, sehingga perubahan role atau status akun baru berlaku setelah token kedaluwarsa.
- Registrasi menerima `role` dari klien. Hanya `admin` yang ditolak (403). Siapa pun dapat mendaftar sebagai `advisor`. Ini perilaku yang ada dan sengaja tidak diubah, menunggu keputusan.
- Peran `advisor` saat ini hanya punya akses ke feedback, sehingga dampak pendaftaran mandiri sebagai advisor terbatas pada endpoint itu.
- Beberapa endpoint assessment hanya diperiksa lewat role. Kepemilikan assessment per pengguna tidak diaudit di dokumen ini.

