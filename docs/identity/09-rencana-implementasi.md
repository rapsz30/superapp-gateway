# 09. Rencana Implementasi

Belum dimulai. Urutan dirancang agar tiap tahap bisa diuji sendiri dan tidak merusak layanan yang berjalan.

## Tahap

| # | Tahap | Hasil | Uji |
|---|---|---|---|
| 0 | Kerangka layanan `services/identity` (FastAPI, SQLAlchemy, Alembic, Dockerfile), `.env.example` | layanan hidup dengan `/health` | smoke |
| 1 | Migrasi: fakultas, jurusan, prodi, orang, akun | tabel dan batasan | uji migrasi naik dan turun |
| 2 | Migrasi: penugasan, keanggotaan, bimbingan, panduan, audit | semua indeks unik parsial dan CHECK | uji pelanggaran batasan |
| 3 | Auth: login, refresh, logout, ganti sandi, `saya`, CLI superadmin | token dengan klaim sesuai | uji unit dan integrasi |
| 4 | CRUD struktur + penutupan unit + `/struktur` | superadmin bisa membangun pohon | uji integrasi |
| 5 | Orang, akun, impor CSV | laporan impor per baris | uji dengan CSV berisi baris rusak |
| 6 | Penugasan, keanggotaan, bimbingan, pindahkan massal | aturan jumlah tegak | uji aturan dan kasus tepi |
| 7 | Panduan berversi (unggah, aktifkan, arsip) | satu versi aktif per prodi | uji balapan dua aktivasi |
| 8 | Penyaringan cakupan unit di semua endpoint baca | tiap peran hanya melihat miliknya | matriks uji peran × endpoint |
| 9 | Audit log | semua perubahan tercatat | uji isi sebelum dan sesudah |
| 10 | Integrasi gateway: compose, NGINX, verifier, rahasia JWT bersama | `/api/identity/*` lewat 8080 | smoke test gateway diperluas |
| 11 | Komentar DEPRECATED di kode dan dokumen lama | daftar di [07](07-integrasi-dan-deprecation.md) | tinjau diff, tanpa perubahan perilaku |
| 12 | Dokumentasi akhir dan pembaruan port-map, nginx-routing, auth-gateway, CI | dokumen sinkron | tinjau |

Tahap 10 dan 11 dikerjakan terakhir supaya layanan lama tidak terganggu selama pengembangan.

## Struktur kode yang diusulkan

```
services/identity/
  alembic/versions/
  src/
    api/routes/        auth.py, struktur.py, orang.py, penugasan.py, bimbingan.py, panduan.py, audit.py
    api/schemas/
    core/              config.py, security.py (hash, JWT), cakupan.py
    domain/            aturan jabatan, validasi peran dan unit
    infrastructure/db/ models.py, session.py
    cli.py             buat-superadmin
  tests/unit, tests/integration
  Dockerfile
  pyproject.toml
```

Memakai tata letak yang sama dengan Micro-cred supaya mudah dibaca tim.

## Strategi uji

- Uji batasan database langsung (insert yang harus gagal).
- Matriks hak akses: setiap peran × setiap endpoint, memastikan 200, 403, atau 404 sesuai [03](03-peran-dan-hak-akses.md).
- Uji token: kedaluwarsa, `tv` lama, peran tidak dikenal, algoritma `none`.
- Uji impor CSV: baris ganda, NIM duplikat, huruf besar pada email.
- Uji balapan: dua aktivasi panduan dan dua penugasan kaprodi bersamaan.
- Smoke test gateway: login lewat 8080, akses rute terproteksi, peran salah ditolak.
- Uji performa ringan pada `/auth/login` dengan skrip yang sudah ada di `gateway/tests/perf`.

## Kriteria selesai

1. Seluruh uji lulus di CI.
2. Superadmin dapat membangun fakultas sampai prodi, menugaskan jabatan, menetapkan PA, dan mengaktifkan panduan hanya lewat API.
3. Tidak ada data di Micro-cred atau PocketBase yang berubah.
4. `docs/` sinkron dengan perilaku sebenarnya.

## Risiko

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Struktur resmi kampus berbeda dari asumsi | skema perlu diubah | konfirmasi A1 sampai A5 sebelum tahap 1 |
| Rahasia JWT bersama tidak sinkron | semua token ditolak | satu sumber rahasia, smoke test setelah deploy |
| Tahap lanjutan (migrasi layanan lain) tertunda | dua sistem akun berjalan lama | batas tegas dan tanggal di komentar DEPRECATED |
| Port bentrok di mesin pengembang | layanan tidak jalan | cek port-map; ingat insiden port 3000 pada proyek lain |

## Status implementasi (2026-11-25)

Semua tahap 0 sampai 12 selesai. Penyimpangan dari rancangan awal:

| Hal | Rancangan | Yang dibuat | Alasan |
|---|---|---|---|
| Tanggal selesai penugasan | inklusif | **eksklusif** (`selesai > hari ini` berarti masih aktif) | agar mengakhiri hari ini langsung efektif dan pengganti boleh mulai di hari yang sama |
| Cakupan di token | dipakai layanan untuk menyaring | token membawa `scopes`, tetapi **cakupan dihitung ulang dari database** pada setiap request | perubahan jabatan langsung berlaku di identity, bukan menunggu token habis |
| Pemeriksaan `tv` (versi token) | hanya endpoint sensitif | **semua** endpoint identity | murah (satu baca) dan lebih aman |
| Endpoint status keanggotaan | tidak ada | `POST /keanggotaan/{id}/status` | lulus, keluar, cuti perlu jalur sendiri |
| Hash sandi | argon2id | **bcrypt** (rounds 12) | sama dengan Micro-cred, tanpa dependensi native tambahan |
| Pembatas laju login | tidak dirinci | dalam memori per (email, alamat) | cukup untuk satu instance; perlu Redis bila identity dijalankan lebih dari satu replika |
| Email pada login | EmailStr | string biasa | login tidak boleh menolak alamat yang sudah terdaftar |

Pemeriksaan `tv` di verifier gateway sudah ada (endpoint internal `/internal/akun/{id}/versi-token`, cache 5 detik, fail closed, NGINX memblokir `/api/identity/internal/`). Pengajuan ke DPA: [12](12-pengajuan-ke-dpa.md).

Yang belum dikerjakan (di luar tahap ini): lupa sandi lewat email, SSO kampus, memindahkan layanan lain ke akun baru.


## Pembaruan: pengajuan ke DPA lewat proses AlurKerja lengkap

Connector dan BPMN StudentGateway dipindahkan ke repo ini; langkah AI (baca KHS, rekomendasi, revisi) dikerjakan worker lewat endpoint `/api/matkul/*` di matkul, dengan panduan per prodi dari identity. Lihat [12](12-pengajuan-ke-dpa.md) dan [13](13-proses-alurkerja-penuh.md).
