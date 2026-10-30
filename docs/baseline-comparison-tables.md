# Tabel Hasil Pengujian Baseline Fase A (`docs/baseline-comparison-tables.md`)

Dihasilkan oleh: `powershell -File gateway/tests/baseline/run-baseline.ps1 -Report`  
Sumber data: `gateway/tests/baseline/out/phase-a-summary.json`  
- Waktu mulai eksperimen (UTC): `tidak diukur`  
- Waktu selesai / pembaruan terakhir (UTC): `tidak diukur`  
- Ulangan yang diminta: `tidak diukur`  
- Ulangan yang berhasil diselesaikan: `tidak diukur`  
- Kondisi K2 (opsional): `tidak diukur`  

> [!NOTE]
> Metadata di atas dibaca apa adanya dari `phase-a-summary.json`. Bila metadata tidak tersedia, ditulis **`tidak diukur`** (tidak diisi dugaan).
>
> **K2 bersifat opsional**: K2 (PDF valid) hanya dijalankan bila hasil pembacaan kode dan verifikasi satu request langsung menunjukkan prasyarat terpenuhi (HTTP 200, `extracted_chars` > 0, tanpa LLM dan tanpa efek samping). Bila tidak dijalankan, barisnya ditulis `tidak diukur` dan **bukan** dianggap gagal.
>
> Sel tanpa data pengukuran aktual ditulis **`tidak diukur`** (tidak diestimasi dan tidak diisi nol).

---

## 1. Tabel Tiga Jalur per Kondisi (`direct`, `noauth`, `gateway`)

| Kondisi | Layanan | Endpoint | Laju Target (req/s) | Jalur | p50 Median [Minâ€“Maks] (ms) | p95 Median [Minâ€“Maks] (ms) | p99 Median (ms) | Rata-rata (ms) | Throughput (req/s) | Kegagalan (%) | Dropped Iterations | Interval Stats Median (s) |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | Judul | `GET /` | 50 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | Judul | `GET /` | 50 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | Judul | `GET /` | 50 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | Judul | `GET /` | 200 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | Judul | `GET /` | 200 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | Judul | `GET /` | 200 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 10 | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 10 | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 10 | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

---

## 2. Tabel Selisih Antar Jalur ($\Delta_{\text{proxy}}$, $\Delta_{\text{auth}}$, $\Delta_{\text{total}}$) dan Tafsir

**Catatan metodologis:**
- Fokus utama analisis overhead adalah **p50 dan p95**. p99 dan rata-rata tetap disajikan pada tabel pertama (Bagian 1) sebagai data pelengkap, dan tidak dihitung selisihnya.
- Angka dalam tanda kurung siku `[Min..Maks]` adalah **rentang antar-ulangan**: selisih per ulangan (jalur A minus jalur B pada nomor ulangan yang sama), BUKAN rentang variasi tiap request individual.
- Aturan tafsir: bila rentang p50 dua jalur saling tumpang tindih, ditulis `tidak dapat dibedakan pada pengukuran ini`.
- Dengan sedikit ulangan, rentang antar-ulangan hanya gambaran kasar variabilitas, bukan interval kepercayaan statistik.

| Kondisi | $\Delta_{\text{proxy}}$ p50 [Minâ€“Maks] (ms) | $\Delta_{\text{auth}}$ p50 [Minâ€“Maks] (ms) | $\Delta_{\text{total}}$ p50 [Minâ€“Maks] (ms) | $\Delta_{\text{proxy}}$ p95 [Minâ€“Maks] (ms) | $\Delta_{\text{auth}}$ p95 [Minâ€“Maks] (ms) | $\Delta_{\text{total}}$ p95 [Minâ€“Maks] (ms) | Tafsir $\Delta_{\text{proxy}}$ | Tafsir $\Delta_{\text{auth}}$ | Tafsir $\Delta_{\text{total}}$ |
|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

---

## 3. Median CPU dan Memori per Container pada Fase Ukur (Dua Tabel Terpisah)

Nilai adalah **median** sampel `docker stats` pada jendela fase ukur 30 detik (bukan puncak), lalu median antar-ulangan. `100%` CPU = 1 core logis penuh. Kolom `superapp-nginx-noauth` hanya terisi pada jalur `noauth`.

### 3.1. Median CPU (%) per Container

| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |
|---|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-20rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-20rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

### 3.2. Median Memori (MiB) per Container

| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |
|---|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-20rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-20rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M1-100rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-20rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **M2-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **J1-200rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-20rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K1-50rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-5rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

