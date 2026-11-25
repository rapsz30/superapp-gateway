# Layanan Identity

Akun, struktur organisasi (fakultas → jurusan → prodi), peran, relasi dosen PA dengan mahasiswa, dan panduan akademik per prodi (berversi). Rancangan lengkap: [docs/identity](../../docs/identity/README.md).

Diakses lewat gateway: `http://127.0.0.1:8080/api/identity/*`. Debug langsung: `http://127.0.0.1:8002/docs`.

## Menjalankan bersama gateway

```powershell
Copy-Item services\identity\.env.example services\identity\.env
# isi JWT_SECRET (sama dengan services\microcred\.env) dan sandi database
docker compose up -d --build identity-db identity-api
docker compose exec identity-api python -m src.cli buat-superadmin --email admin@kampus.ac.id --nama "Nama Admin"
```

Sandi sementara dicetak sekali; akun wajib mengganti sandi saat login pertama. Migrasi (Alembic) berjalan otomatis saat container start.

## Menjalankan uji

Uji memakai Postgres sungguhan karena indeks unik parsial, CHECK, dan trigger audit adalah bagian dari perilaku yang diuji.

```powershell
docker run -d --name identity-test-db -e POSTGRES_USER=identity -e POSTGRES_PASSWORD=identity -e POSTGRES_DB=identity_test -p 127.0.0.1:55433:5432 postgres:15.5
cd services\identity
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

`TEST_DATABASE_URL` mengganti alamat database uji. Database uji dikosongkan setiap tes, jangan diarahkan ke data sungguhan.

## Struktur

```
src/api/        main.py, deps.py, errors.py, schemas.py, routes/
src/core/       config.py, security.py (hash, JWT), waktu.py
src/domain/     cakupan.py (peran dan cakupan unit), audit.py, token_service.py
src/models.py   model dan batasan database
alembic/        migrasi
tests/
```

## Catatan keamanan

- `JWT_SECRET` wajib minimal 32 karakter; layanan menolak start bila kosong atau berisi nilai bawaan.
- Token akses 15 menit; token penyegar 7 hari, sekali pakai (rotasi) dengan deteksi pemakaian ulang.
- Hak akses dihitung dari database pada setiap request, tidak dari klaim token.
- Sandi sementara hanya tampil sekali (respons pembuatan akun, atur ulang, atau laporan impor) dan tidak masuk audit log.
- Audit log hanya-tambah; database menolak UPDATE dan DELETE.
- `/internal/*` hanya untuk verifier gateway: wajib `X-Internal-Token`, dan diblokir NGINX dari luar.
- Pengajuan ke DPA ([docs/identity/12](../../docs/identity/12-pengajuan-ke-dpa.md), [13](../../docs/identity/13-proses-alurkerja-penuh.md)): identity memulai proses AlurKerja dan menyalin keadaannya; langkah AI dikerjakan worker dan matkul.
- Unggah panduan mengekstrak teks (`pypdf`); PDF scan, rusak, atau terkunci ditolak. `GET /akademik/konteks` dipakai matkul sebagai dasar rekomendasi ([docs/identity/11](../../docs/identity/11-integrasi-matkul.md)).
