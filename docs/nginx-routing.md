# Routing NGINX Gateway

Gateway berjalan di `127.0.0.1:8080`. Konfigurasi: `gateway/nginx/nginx.conf`.

## Tabel rute

| Prefix publik | Upstream | Path setelah prefix dibuang |
|---|---|---|
| `/api/matkul-recommender/*` | `matkul:3000` | `/api/*` (contoh: `/api/matkul-recommender/khs/upload` → `/api/khs/upload`) |
| `/api/judul-recommender/*` | `judul-api:8001` | `/*` (contoh: `/get-recommendations`) |
| `/api/micro-cred/*` | `microcred-api:8000` | `/*` (contoh: `/auth/login`) |
| `/healthz` | dijawab NGINX | `200 {"status":"ok"}` |
| lainnya | - | `404 {"detail":"Not found"}` |

Hanya rute API Matkul yang di-proxy, halaman UI tidak termasuk.
Header `Authorization` diteruskan apa adanya (belum ada autentikasi di gateway).

## Batas upload

| Lokasi | `client_max_body_size` |
|---|---|
| Matkul | 16m |
| Lainnya | 1m |

Melebihi batas → `413 {"detail":"Ukuran file melebihi batas"}`.

## Timeout

| Lokasi | connect | read / send |
|---|---|---|
| Matkul | 5s | 120s |
| Judul, Micro-cred | 5s | 60s |

`client_body_timeout` 60s untuk semua lokasi.

## Alasan angka

Batas 16m di Matkul dipilih karena batas aplikasi 15 MB, sisanya untuk overhead multipart, sedangkan layanan lain hanya menerima JSON kecil sehingga 1m cukup. Timeout baca/kirim Matkul 120s karena layanan ini memanggil LLM dengan teks panduan yang panjang sehingga responsnya lebih lambat, sementara Judul dan Micro-cred cukup 60s. Connect timeout 5s agar kegagalan upstream (mati/tidak terjangkau) cepat terdeteksi dan dijawab 502/504 JSON. Error 502/503/504 dijawab `{"detail":"Layanan tidak tersedia"}`.

