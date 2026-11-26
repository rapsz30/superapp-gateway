# Deploy ke VPS

**Status (26 Nov 2026):** image frontend sudah dibangun dan dicoba di laptop terhadap gateway lokal; susunan compose produksi dan isi arsip sudah diperiksa. **Skrip belum pernah dijalankan ke server sungguhan.** Baca juga [temuan audit](audit-deploy-vps.md).

## Bagian-bagian

| Berkas | Guna |
|---|---|
| `deploy/deploy-vps.sh` | kemas commit, unggah, cadangkan basis data, build, nyalakan, periksa, rollback |
| `deploy/deploy.env.example` | alamat server dan port (salin ke `deploy/deploy.env`, tidak masuk git) |
| `docker-compose.prod.yml` | layanan `frontend`, Caddy (profil `https`), batas ukuran log |
| `frontend/Dockerfile` | image web |
| `deploy/Caddyfile` | HTTPS otomatis untuk server kosong |
| `deploy/nginx-host.conf.example` | untuk server yang sudah punya NGINX |

Dari luar hanya proxy HTTPS yang terjangkau. Frontend (`3200`) dan gateway (`8080`) mendengar di `127.0.0.1`.

## 1. Siapkan server

- Ubuntu atau sejenisnya, RAM minimal 2 GB untuk superapp saja (AlurKerja di server yang sama: minimal 8 GB).
- Docker Engine dan plugin Compose, `curl`; pengguna SSH boleh menjalankan `docker`.
- Firewall membuka 22, 80, 443 saja. Ingat: port Docker yang dipublikasikan ke `0.0.0.0` bisa melewati UFW.
- DNS domain menunjuk ke server.
- Masuk memakai kunci SSH.

## 2. Siapkan di laptop

Salin `deploy/deploy.env.example` menjadi `deploy/deploy.env`, lalu isi. Pilih `PROXY=caddy` hanya bila port 80 dan 443 belum dipakai; selain itu `PROXY=ada`.

Skrip hanya mengirim **commit terakhir**, jadi commit dulu. Dijalankan dari Git Bash:

```bash
./deploy/deploy-vps.sh kemas      # coba kemas, tidak menyentuh server
./deploy/deploy-vps.sh siapkan    # pertama kali: buat berkas .env di server
```

## 3. Isi `.env` di server

Cara cepat (khusus server `alurkerja.ahlanapp.cloud`; alamat dan id tenant tertulis di dalam skrip): salin `deploy/isi-env.py` ke `~/superapp/`, lalu jalankan `python3 ~/superapp/isi-env.py`. Rahasia internal dibuat acak; kunci OpenAI, Groq, dan akun layanan Camunda diketik sendiri. Tabel di bawah untuk pengisian manual.

Berkasnya ada di `~/superapp/env/` (sesuai `REMOTE_DIR`). Buat secret **baru** dengan `openssl rand -hex 32`; jangan menyalin dari laptop.

| Berkas | Yang harus diisi |
|---|---|
| `services/identity/.env` | `POSTGRES_PASSWORD` dan sandi yang sama di `DATABASE_URL`; `JWT_SECRET`; `INTERNAL_TOKEN`; `MATKUL_SERVICE_TOKEN`; semua `ALURKERJA_*` untuk AlurKerja server |
| `services/matkul/.env.local` | `OPENAI_API_KEY`; `POSTGRES_PASSWORD` dan `DATABASE_URL`; `MATKUL_SERVICE_TOKEN` dan `INTERNAL_TOKEN` (**sama** dengan identity); `PB_ADMIN_*` |
| `services/microcred/.env` | `APP_ENV=production`; `JWT_SECRET` (**berbeda** dari identity); `POSTGRES_PASSWORD` dan `DATABASE_URL`; kunci lain boleh isi tiruan selama fiturnya ditunda |
| `services/judul/.env` | `GROQ_API_KEY` |
| `alurkerja-connector/.env` | `ALURKERJA_BASE_URL`, akun worker, `GATEWAY_TOKEN` (**sama** dengan `MATKUL_SERVICE_TOKEN`) |

- Sertifikat AlurKerja asli (Let's Encrypt dan sejenisnya): kosongkan `ALURKERJA_CA_BUNDLE`.
- Sertifikat buatan sendiri: taruh root CA di `~/superapp/env/rootCA.pem` dan set `ALURKERJA_CA_BUNDLE=/certs/rootCA.pem`.
- Biarkan `ALURKERJA_ADMIN_CLIENT_SECRET` kosong (sinkron akun dimatikan).
- AlurKerja belum ada: kosongkan `ALURKERJA_URL` di identity (mode lokal, keputusan lewat web). Connector akan gagal tersambung sampai alamatnya diisi.

## 4. Deploy

```bash
./deploy/deploy-vps.sh
```

Urutannya: periksa arsip, unggah, periksa `.env`, cadangkan tiga basis data (mulai deploy kedua), build saat versi lama masih melayani, nyalakan, periksa kesehatan gateway dan web. Bila gagal, rilis sebelumnya dinyalakan lagi. Rollback **tidak membatalkan perubahan skema** basis data.

## 5. Sekali setelah deploy pertama

Di server:

```bash
cd ~/superapp/current
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec identity-api \
  python -m src.cli buat-superadmin --email admin@kampusmu.ac.id --nama "Admin"
```

- **Proxy:** bila `PROXY=ada`, pasang `deploy/nginx-host.conf.example` lalu `certbot`.
- **AlurKerja:** deploy Live kedua BPMN, buat form, dashboard, Auth Token, akun dosen; isi id tenant dan dashboard di `.env` identity, lalu deploy ulang. Rinciannya di [13](identity/13-proses-alurkerja-penuh.md) dan [14](identity/14-pengajuan-judul-ta.md).
- **Isi data:** struktur organisasi, akun, penugasan, panduan akademik lewat halaman admin.

## Cadangan dan pemulihan

Cadangan dibuat skrip tiap deploy di `~/superapp/backup/`. Itu **bukan cadangan terjadwal**; tambahkan cron bila datanya penting. Berkas panduan (volume `identity_panduan`) tidak ikut. Contoh memulihkan identity ke basis data kosong:

```bash
gunzip -c ~/superapp/backup/<waktu>-identity-db.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T identity-db \
  sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Pemulihan ini belum pernah diuji.

## Belum ditangani

Pembatasan laju, rute AI langsung, dan micro-credential (ditunda atas keputusan pemilik proyek). Rute pendaftaran publik micro-credential ikut terbuka di server.
