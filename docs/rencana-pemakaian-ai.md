# Serah terima: pantauan pemakaian AI untuk admin

Dokumen untuk agen pelaksana. Disusun 27 November 2026.

## Tujuan

Superadmin dapat memantau pemakaian AI aplikasi: jumlah panggilan, token, kegagalan, per fitur, per hari, dan per pengguna.

Di luar cakupan: tagihan resmi (acuannya dasbor OpenAI), pembatasan kuota, dan pemakaian sebelum fitur terpasang.

## Aturan yang harus dipegang

- Isi prompt dan jawaban AI **tidak disimpan** (memuat data KHS dan esai mahasiswa).
- Pencatatan tidak boleh menggagalkan atau memperlambat berarti fitur utama. Batas waktu pendek, galat hanya masuk log.
- Token pencatatan (`AI_CATAT_TOKEN`) terpisah dari `INTERNAL_TOKEN`, supaya pemegangnya hanya bisa menambah catatan.
- Harga token diisi pemilik proyek lewat env. Jangan menebak harga.
- Jangan commit, push, atau deploy tanpa diminta.

## Keadaan kode saat dokumen ditulis

Di working tree `superapp-gateway` sudah ada **draf bagian identity** (belum di-commit). Draf ini belum lolos tes: satu galat 204 sudah diperbaiki, tetapi rangkaian tesnya belum selesai dijalankan ulang. Pemilik proyek memutuskan draf ini **disimpan** untuk dilanjutkan. Jangan deploy folder kerja sebelum draf selesai dan lolos tes.

| Berkas | Isi draf |
|---|---|
| `services/identity/alembic/versions/0008_ai_pemakaian.py` | baru: tabel |
| `services/identity/src/api/routes/ai_pemakaian.py` | baru: endpoint catat dan ringkasan |
| `services/identity/tests/test_ai_pemakaian.py` | baru: tes |
| `services/identity/src/models.py` | model `AiPemakaian` |
| `services/identity/src/core/config.py` | `ai_catat_token`, `ai_harga_masuk_per_juta`, `ai_harga_keluar_per_juta` |
| `services/identity/src/api/main.py` | daftar router |
| `services/identity/src/integrations/judul.py` | `atas_nama(akun_id)` mengirim header `X-User-Id` ke judul |
| `services/identity/src/api/routes/judul.py`, `obrolan_judul.py` | memakai `atas_nama` |
| `services/identity/tests/conftest.py` | tabel baru ikut dikosongkan |

Berkas lain yang belum di-commit (merge micro credential, autentikasi identity di microcred, model `gpt-6-luna`, timeout AlurKerja, `isi-env.py`) adalah pekerjaan lain. **Jangan dibuang.** `services/identity/src/integrations/alurkerja.py` termasuk pekerjaan lain itu.

Image `superapp-identity-api` lokal sempat di-build ulang dengan draf ini, sedangkan container yang berjalan masih image lama. `docker compose up -d` akan memakai image baru dan menjalankan migrasi 0008. Build ulang dulu bila draf dibuang.

## Titik pemanggilan AI

| Layanan | Berkas | Nama `fitur` | Pemilik pemakaian |
|---|---|---|---|
| matkul | `src/lib/openai.ts` (`extractKhsFromText`) | `baca_khs` | header `X-User-Id`, atau `pengajuan_id` pada langkah proses |
| matkul | `src/lib/proses/recommend.ts` | `rekomendasi_matkul` | sama |
| matkul | `app/api/rekomendasi/route.ts` | `rekomendasi_pratinjau` | header `X-User-Id` |
| judul | `services/ai_service.py` (`_call_openai_api`) | `rekomendasi_judul` | header `X-User-Id` |
| judul | `services/obrolan_service.py` (`balas`) | `obrolan_judul` | header `X-User-Id` |
| microcred | `src/libs/gpt_client.py`, dipanggil `src/domain/services/gpt_scoring.py` | `nilai_esai` | `owner_id` asesmen (sama dengan id akun identity) |

`services/judul/main_backup.py` tidak dipakai. Setiap percobaan ulang dihitung sebagai satu panggilan.

## Kontrak API identity

### `POST /internal/ai-pemakaian`

Header `X-AI-Token`. Salah atau token tidak diatur: 404. NGINX sudah menutup `/api/identity/internal/`; layanan memanggil `http://identity-api:8002` langsung.

```json
{
  "layanan": "matkul | judul | microcred",
  "fitur": "huruf_kecil_dan_garis_bawah, maks 40",
  "model": "gpt-6-luna",
  "token_masuk": 0,
  "token_keluar": 0,
  "durasi_ms": 0,
  "berhasil": true,
  "akun_id": "uuid, opsional",
  "pengajuan_id": "uuid, opsional; dipakai mencari akun mahasiswa bila akun_id kosong"
}
```

Balasan 204. Panggilan gagal dicatat dengan `berhasil: false` dan token 0.

### `GET /ai-pemakaian?dari=YYYY-MM-DD&sampai=YYYY-MM-DD`

Khusus superadmin. Tanggal inklusif menurut zona kampus, bawaan 30 hari terakhir, maksimal 366 hari (di luar itu 400).

```json
{
  "dari": "2026-10-29",
  "sampai": "2026-11-27",
  "harga": null,
  "total": {"panggilan": 0, "gagal": 0, "token_masuk": 0, "token_keluar": 0, "biaya_usd": null},
  "per_hari": [{"tanggal": "2026-11-27", "panggilan": 0, "gagal": 0, "token_masuk": 0, "token_keluar": 0}],
  "per_fitur": [{"layanan": "judul", "fitur": "obrolan_judul", "model": "gpt-6-luna", "rata_durasi_ms": 0,
                 "panggilan": 0, "gagal": 0, "token_masuk": 0, "token_keluar": 0}],
  "per_pengguna": [{"akun_id": null, "nama": null, "email": null,
                    "panggilan": 0, "gagal": 0, "token_masuk": 0, "token_keluar": 0}]
}
```

`per_hari` memuat semua tanggal dalam rentang. `per_pengguna` maksimal 20, urut token terbanyak. `harga` terisi `{"masuk_per_juta", "keluar_per_juta"}` hanya bila kedua env diisi; `biaya_usd` mengikuti.

## Pengirim catatan

- **matkul** (Node): satu modul, misalnya `src/lib/ai-catat.ts`. Teruskan pemilik dengan `AsyncLocalStorage` dari route ke pemanggilan AI. Kirim tanpa ditunggu, `AbortSignal.timeout(3000)`. Ambil `completion.usage.prompt_tokens` dan `completion_tokens`. Tes memuat berkas `.ts` langsung dengan `node --test`, jadi impor antar-berkas memakai path relatif berakhiran `.ts`. Hasil baca KHS yang diambil dari cache tidak memanggil AI, jadi tidak dicatat.
- **judul** (Python): middleware menyimpan `X-User-Id` di `ContextVar`; bungkus `chat.completions.create`; kirim di thread terpisah supaya identity yang sedang menunggu judul tidak saling menunggu. `requirements.txt` berkas UTF-16, jadi hindari dependensi baru (`urllib` cukup).
- **microcred** (Python): tambah setting `ai_catat_token` (`identity_url` sudah ada). Catat di `OpenAIClient.chat_completion`, pemilik lewat `ContextVar` yang diisi `gpt_scoring`. Antarmuka `GPTClientProtocol` jangan berubah (dipakai mock di tes). Skor cadangan berbasis aturan bukan panggilan AI.

## Halaman admin

- Rute `frontend/app/admin/ai/page.tsx`, komponen di `frontend/components/admin/`.
- Menu "Pemakaian AI" di `admin-shell.tsx` dengan `superOnly: true`, dan tambahkan penjaga yang sama seperti `/admin/audit` (saat ini diperiksa berdasarkan path).
- Ikuti pola yang ada: Ant Design, `recharts`, `useLoad` dari `components/admin/ui.tsx`, layanan di `src/services/admin-service.ts`.
- Isi: pemilih rentang tanggal; kartu panggilan, gagal, token masuk, token keluar, perkiraan biaya (tampil hanya bila `harga` ada); grafik harian; tabel per fitur; tabel pengguna. `akun_id` kosong ditampilkan "Tidak diketahui".
- Beri keterangan di halaman: angka hanya dari aplikasi ini, sejak pencatatan dipasang.

## Konfigurasi

| Layanan | Env |
|---|---|
| identity | `AI_CATAT_TOKEN`, opsional `AI_HARGA_MASUK_PER_JUTA`, `AI_HARGA_KELUAR_PER_JUTA` (USD) |
| matkul, judul, microcred | `AI_CATAT_TOKEN` (sama dengan identity), `IDENTITY_URL=http://identity-api:8002` |

- `IDENTITY_URL` diisi di `docker-compose.yml` untuk judul (microcred sudah; matkul punya bawaan).
- Tambahkan nama env ke `.env.example` tiap layanan, nilai kosong = pencatatan mati.
- `deploy/isi-env.py`: buat token acak sekali di identity dan salin ke tiga layanan, seperti pola `INTERNAL_TOKEN`.
- Lokal: isi token di berkas `.env` masing-masing tanpa mencetak nilainya.
- Perbarui `docs/deploy-vps.md`.

## Pengujian

Identity memakai Postgres sungguhan (container `identity-test-db`, port 55433; lihat `tests/conftest.py`). Di laptop ini paket Python tidak terpasang, jadi jalankan di container, dari Git Bash di folder `superapp-gateway`:

```bash
docker compose build identity-api
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W)/services/identity:/src_ro:ro" \
  -e TEST_DATABASE_URL=postgresql+psycopg2://identity:identity@host.docker.internal:55433/identity_test \
  --entrypoint sh --user root superapp-identity-api -c \
  'cp -r /src_ro /tmp/w && cd /tmp/w && rm -f .env && pip install -q pytest==8.3.4 && python -m pytest -q -p no:warnings'
```

| Bagian | Perintah |
|---|---|
| microcred | `docker compose up -d --build microcred-api`, lalu `docker compose exec microcred-api poetry run pytest -q` (terakhir 178 lolos) |
| matkul | `pnpm test` di `services/matkul` |
| frontend | `npx tsc --noEmit -p .` (build melewati cek tipe), `npm run build`, `npm test` |

Sesudah membuat ulang container: `docker compose exec nginx nginx -s reload` agar tidak 502.

## Selesai bila

1. Tes tiap layanan lolos, termasuk tes bahwa kegagalan pencatatan tidak menggagalkan fitur.
2. Secara lokal, satu pemakaian dari matkul, judul, dan microcred muncul di `/admin/ai` atas pengguna yang benar.
3. Non-superadmin ditolak (403) dan `/api/identity/internal/ai-pemakaian` menjawab 404 lewat gateway.
4. Tidak ada isi prompt, jawaban, token, atau kunci di tabel maupun log.

## Catatan deploy

Migrasi identity berjalan otomatis saat container menyala. Migrasi microcred tidak otomatis (lihat `docs/deploy-vps.md`). `IKUT_BELUM_COMMIT=1` mengirim seluruh folder kerja, termasuk draf yang belum selesai.
