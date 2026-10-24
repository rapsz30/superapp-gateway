# Baseline sources
- judul-ta : commit 294e094 + local changes (docs/baseline/judul-ta-local-changes.patch)
- matkul   : commit 23e3a54 + local changes (docs/baseline/matkul-local-changes.patch)
- microcred: commit 6eba075 + local changes (docs/baseline/microcred-local-changes.patch)
Copied on 2026-10-15. Source folders are kept untouched in ../recommender.

- microcred: docker-compose.yml diganti nama menjadi docker-compose.standalone.yml supaya tidak tertukar dengan docker-compose.yml di root repo.

## Perubahan microcred: identitas mahasiswa

### Alasan
Login dan registrasi Micro-cred akan menjadi login dan registrasi SuperApp, sehingga registrasi kini menyimpan identitas mahasiswa (nama, NIM, fakultas, program studi).

### File yang diubah (di `services/microcred`)
- `src/infrastructure/db/models.py` (model `UserModel`)
- `src/api/schemas/auth.py`
- `src/api/routes/auth.py` (meneruskan field baru dan memperbarui deskripsi)
- `src/domain/services/auth_service.py`
- `alembic/versions/202610240001_add_student_identity_to_users.py` (baru)
- Tes: `tests/integration/test_auth_routes.py`, `tests/unit/test_auth_service.py`

### Kolom dan migrasi
Tabel `users` mendapat tiga kolom nullable (akun lama tetap valid): `nim` (string 32, unik, index `ix_users_nim`), `faculty` (string 100), `study_program` (string 100). Revisi `202610240001` berinduk `202602170001`. Migrasi tidak berjalan otomatis saat container start, jadi dijalankan manual setelah rebuild:

```
docker compose up -d --build microcred-api microcred-worker
docker compose exec microcred-api poetry run alembic upgrade head
```

Setelah rebuild, restart juga NGINX (`docker compose restart nginx`) bila ia tidak ikut dibuat ulang, karena IP upstream berubah.

### Aturan validasi (`POST /auth/register`)
| Field | Aturan |
|---|---|
| `full_name` | wajib, di-strip, 2 sampai 128 karakter |
| `nim` | wajib, di-strip, hanya digit, 6 sampai 15 karakter (konstanta `NIM_MIN_LENGTH` dan `NIM_MAX_LENGTH`; format NIM UII belum dikonfirmasi, batas sengaja longgar) |
| `faculty` | wajib, di-strip, 2 sampai 100 karakter |
| `study_program` | wajib, di-strip, 2 sampai 100 karakter |
| `email`, `password`, `role` | tidak berubah |

NIM atau email yang sudah terdaftar dijawab 409. NIM juga dijaga oleh index unik di database agar aman terhadap permintaan bersamaan. `UserResponse` (juga pada login dan `GET /auth/me`) memuat `nim`, `faculty`, `study_program` (null untuk akun lama). Token JWT tidak memuat field identitas, klaimnya tetap `sub, roles, iat, exp, iss, email`.

### Dampak pada pemanggil registrasi lama
Skrip berikut memanggil `/auth/register` tanpa field baru dan akan mendapat 422 sampai diperbarui (tidak diubah di tugas ini):
- `scripts/test_personalization.py`
- `scripts/test_production_with_mc.py`
- `scripts/test_profiling_questions.py`

### Contoh
Request `POST /auth/register`:
```json
{"email":"mahasiswa@example.com","password":"minimal8kar","full_name":"Nama Lengkap","nim":"12345678","faculty":"Nama Fakultas","study_program":"Nama Program Studi"}
```
Respons 201 (bagian `user`, token dihilangkan):
```json
{"message":"Registration successful","user":{"id":"<uuid>","email":"mahasiswa@example.com","full_name":"Nama Lengkap","nim":"12345678","faculty":"Nama Fakultas","study_program":"Nama Program Studi","role":"student","status":"active","is_verified":false,"created_at":"<timestamp>","last_login_at":null},"tokens":{"...":"..."}}
```
Respons `GET /auth/me`:
```json
{"user":{"id":"<uuid>","email":"mahasiswa@example.com","full_name":"Nama Lengkap","nim":"12345678","faculty":"Nama Fakultas","study_program":"Nama Program Studi","role":"student","status":"active","is_verified":false,"created_at":"<timestamp>","last_login_at":"<timestamp>"}}
```

### Catatan
Penanganan `role` sengaja tidak diubah dan menunggu keputusan. Klien masih dapat memilih `student` atau `advisor` saat registrasi, dan `admin` ditolak (403). Matriks peran lengkap ada di `docs/microcred-roles.md`.