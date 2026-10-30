# Tabel Hasil Pengujian Baseline Fase A (`docs/baseline-comparison-tables.md`)

Dihasilkan oleh: `powershell -File gateway/tests/baseline/run-baseline.ps1 -Report`  
Sumber data: `gateway/tests/baseline/out/phase-a-summary.json` (Waktu sumber: `tidak diukur`, Ulangan target: `tidak diukur`)  

> [!NOTE]
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

## 3. Tabel Median CPU (`%`) dan Memori (`MiB`) per Container pada Fase Ukur

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
