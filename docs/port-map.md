# Peta Port dan Rute

Semua klien memakai satu alamat: `http://127.0.0.1:8080`.

## Rute gateway

| Prefix publik | Service tujuan | Path setelah prefix dibuang |
|---|---|---|
| `/api/matkul-recommender/*` | `matkul:3000` | `/api/*` |
| `/api/judul-recommender/*` | `judul-api:8001` | `/*` |
| `/api/micro-cred/*` | `microcred-api:8000` | `/*` |
| `/healthz` | dijawab NGINX | - |

Detail batas upload dan timeout ada di [nginx-routing.md](nginx-routing.md).

## Port

| Service | Port internal | Port debug (`docker-compose.override.yml`) | Port publik gateway |
|---|---|---|---|
| nginx | 80 | - | `127.0.0.1:8080` |
| microcred-api | 8000 | `127.0.0.1:8000` | lewat `/api/micro-cred` |
| judul-api | 8001 | `127.0.0.1:8001` | lewat `/api/judul-recommender` |
| matkul | 3000 | `127.0.0.1:3000` | lewat `/api/matkul-recommender` (hanya API) |
| pocketbase | 8090 | `127.0.0.1:8090` (admin UI) | - |
| db, redis, microcred-worker | 5432, 6379, - | - | - |

## Dua mode

- Debug (default, memuat override): `docker compose up -d`
- Gateway saja (hanya 8080 terbuka): `docker compose -f docker-compose.yml up -d`

Saat berpindah mode, compose membuat ulang container yang port-nya berubah. NGINX ikut direstart otomatis (`depends_on ... restart: true`) agar tidak memakai IP upstream lama.

## Aturan

- Jangan menjalankan `uvicorn`, `streamlit`, atau `next dev` di host selama stack Docker hidup, karena akan bentrok dengan port debug (mis. WinError 10013 pada port 8000).
- Buka Swagger lewat port debug (`http://127.0.0.1:8000/docs`, `http://127.0.0.1:8001/docs`). Di belakang prefix gateway Swagger umumnya tidak tampil benar tanpa `root_path`, dan kode layanan tidak diubah untuk itu.

## Mengapa gateway, bukan port berbeda per container

Dengan gateway, klien cukup mengenal satu alamat dan satu port, sehingga konfigurasi frontend sederhana dan tidak ada permintaan lintas origin (CORS) antar port. Layanan backend juga tidak terbuka langsung ke host pada mode gateway, jadi satu titik masuk itu yang nanti dapat diberi autentikasi, pembatasan, dan log waktu respons secara seragam.

