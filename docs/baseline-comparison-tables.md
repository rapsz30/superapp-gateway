# Tabel Hasil Pengujian Baseline Fase A (`docs/baseline-comparison-tables.md`)

Dihasilkan oleh: `powershell -File gateway/tests/baseline/run-baseline.ps1 -Report`  
Sumber data: `gateway/tests/baseline/out/phase-a-summary.json`  
- Waktu mulai eksperimen (UTC): `2026-10-30T07:42:06Z`  
- Waktu selesai / pembaruan terakhir (UTC): `2026-10-30T09:30:36Z`  
- Ulangan yang diminta: `3`  
- Ulangan yang berhasil diselesaikan: `min 1, maks 3 per kondisi (10 kondisi tercatat)`  
- Kondisi K2 (opsional): `dijalankan (prasyarat terpenuhi)`  

> [!NOTE]
> Metadata di atas dibaca apa adanya dari `phase-a-summary.json`. Bila metadata tidak tersedia, ditulis **`tidak diukur`** (tidak diisi dugaan).
>
> **K2 bersifat opsional**: K2 (PDF valid) hanya dijalankan bila hasil pembacaan kode dan verifikasi satu request langsung menunjukkan prasyarat terpenuhi (HTTP 200, `extracted_chars` > 0, tanpa LLM dan tanpa efek samping). Bila tidak dijalankan, barisnya ditulis `tidak diukur` dan **bukan** dianggap gagal.
>
> Sel tanpa data pengukuran aktual ditulis **`tidak diukur`** (tidak diestimasi dan tidak diisi nol).

---

## 1. Tabel Tiga Jalur per Kondisi (`direct`, `noauth`, `gateway`)

| Kondisi | Layanan | Endpoint | Laju Target (req/s) | Jalur | p50 Median [Min-Maks] (ms) | p95 Median [Min-Maks] (ms) | p99 Median (ms) | Rata-rata (ms) | Throughput (req/s) | Kegagalan (%) | Dropped Iterations | Interval Stats Median (s) |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `direct` | 5.08 [4.58-5.60] | 9.61 [8.72-680.16] | 10.31 | 6.19 | 20.03 | 0.00% | 0 | 2.06 |
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `noauth` | 5.33 [4.97-5.81] | 8.50 [8.48-8.61] | 10.42 | 5.87 | 20.00 | 0.00% | 0 | 2.06 |
| **M1-20rps** | Micro-cred | `GET /tracks` | 20 | `gateway` | 7.19 [7.11-7.57] | 11.13 [10.96-11.59] | 14.52 | 7.92 | 20.00 | 0.00% | 0 | 2.04 |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `direct` | 4.87 [4.76-4.95] | 7.56 [7.47-63.02] | 8.99 | 5.25 | 50.03 | 0.00% | 0 | 2.04 |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `noauth` | 5.31 [5.23-5.42] | 7.67 [7.57-7.84] | 9.70 | 5.58 | 50.00 | 0.00% | 0 | 2.05 |
| **M1-50rps** | Micro-cred | `GET /tracks` | 50 | `gateway` | 7.06 [6.91-8.69] | 11.18 [10.87-342.15] | 212.39 | 11.27 | 50.03 | 0.00% | 0 | 2.05 |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `direct` | 4.77 [4.77-4.77] | 7.49 [7.49-7.49] | 13.34 | 5.18 | 100.03 | 0.00% | 24 | 2.04 |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `noauth` | 5.50 [5.11-5.88] | 146.31 [50.17-242.45] | 584.79 | 29.16 | 100.03 | 0.00% | 4 | 2.05 |
| **M1-100rps** | Micro-cred | `GET /tracks` | 100 | `gateway` | 76.37 [6.43-146.30] | 2,308.45 [15.29-4,601.60] | 2,564.57 | 822.34 | 56.73 | 19.85% | 492 | 2.06 |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `direct` | 4.41 [4.26-4.58] | 209.49 [7.50-9,194.22] | 1,437.07 | 54.68 | 20.00 | 0.00% | 0 | 2.07 |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `noauth` | 4.81 [4.77-4.84] | 7.64 [6.97-8.06] | 8.93 | 5.20 | 20.03 | 0.00% | 0 | 2.05 |
| **M2-20rps** | Micro-cred | `GET /auth/me` | 20 | `gateway` | 6.51 [6.02-6.89] | 10.28 [9.62-10.55] | 11.51 | 7.05 | 20.03 | 0.00% | 0 | 2.05 |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `direct` | 5.61 [4.32-5.79] | 7.90 [6.43-7.93] | 11.95 | 5.97 | 50.03 | 0.00% | 0 | 2.05 |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `noauth` | 4.89 [4.87-7.01] | 7.67 [7.47-13.41] | 9.82 | 5.22 | 50.03 | 0.00% | 0 | 2.05 |
| **M2-50rps** | Micro-cred | `GET /auth/me` | 50 | `gateway` | 7.37 [6.52-9.02] | 14.31 [11.86-691.86] | 42.23 | 8.95 | 50.03 | 0.00% | 0 | 2.06 |
| **J1-50rps** | Judul | `GET /` | 50 | `direct` | 1.28 [1.27-1.29] | 1.79 [1.76-1.81] | 3.00 | 1.35 | 50.03 | 0.00% | 0 | 2.07 |
| **J1-50rps** | Judul | `GET /` | 50 | `noauth` | 2.09 [2.08-2.10] | 3.16 [3.13-3.32] | 3.84 | 2.21 | 50.03 | 0.00% | 0 | 2.06 |
| **J1-50rps** | Judul | `GET /` | 50 | `gateway` | 4.29 [4.15-4.38] | 6.13 [6.07-6.64] | 9.27 | 4.52 | 50.03 | 0.00% | 0 | 2.07 |
| **J1-200rps** | Judul | `GET /` | 200 | `direct` | 1.16 [1.13-1.17] | 1.60 [1.53-1.65] | 3.62 | 1.23 | 200.03 | 0.00% | 0 | 2.06 |
| **J1-200rps** | Judul | `GET /` | 200 | `noauth` | 1.77 [1.72-1.88] | 2.63 [2.59-3.12] | 5.02 | 1.87 | 200.03 | 0.00% | 0 | 2.07 |
| **J1-200rps** | Judul | `GET /` | 200 | `gateway` | 3.51 [3.37-3.72] | 6.15 [5.80-7.87] | 15.05 | 3.87 | 200.03 | 0.00% | 0 | 2.07 |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `direct` | 3.82 [3.64-4.02] | 5.91 [5.58-5.94] | 9.26 | 4.09 | 20.03 | 0.00% | 0 | 2.07 |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `noauth` | 4.25 [4.04-4.71] | 7.16 [6.83-7.42] | 9.32 | 4.55 | 20.03 | 0.00% | 0 | 2.06 |
| **K1-20rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 20 | `gateway` | 6.48 [6.23-6.49] | 9.75 [9.47-10.24] | 13.44 | 6.88 | 20.03 | 0.00% | 0 | 2.06 |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `direct` | 3.24 [3.07-3.62] | 6.10 [4.42-150.43] | 18.82 | 3.92 | 50.03 | 0.00% | 0 | 2.40 |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `noauth` | 4.01 [3.99-4.08] | 8.38 [7.77-156.47] | 26.13 | 4.82 | 50.00 | 0.00% | 0 | 2.12 |
| **K1-50rps** | Matkul | `POST /api/panduan/extract-upload (non-PDF -> 400)` | 50 | `gateway` | 6.79 [6.62-8.30] | 30.54 [18.22-3,045.49] | 408.57 | 18.66 | 50.00 | 0.00% | 0 | 2.12 |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `direct` | 8.05 [8.05-8.05] | 14.47 [14.47-14.47] | 21.46 | 8.71 | 5.00 | 1.33% | 0 | 2.09 |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `noauth` | 11.95 [11.95-11.95] | 28.45 [28.45-28.45] | 49.83 | 14.41 | 5.03 | 0.00% | 0 | 2.09 |
| **K2-5rps** | Matkul | `POST /api/panduan/extract-upload (PDF valid -> 200)` | 5 | `gateway` | 3,281.73 [3,281.73-3,281.73] | 3,364.25 [3,364.25-3,364.25] | 3,364.79 | 3,203.17 | 0.50 | 100.00% | 0 | tidak diukur |
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

| Kondisi | $\Delta_{\text{proxy}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{auth}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{total}}$ p50 [Min-Maks] (ms) | $\Delta_{\text{proxy}}$ p95 [Min-Maks] (ms) | $\Delta_{\text{auth}}$ p95 [Min-Maks] (ms) | $\Delta_{\text{total}}$ p95 [Min-Maks] (ms) | Tafsir $\Delta_{\text{proxy}}$ | Tafsir $\Delta_{\text{auth}}$ | Tafsir $\Delta_{\text{total}}$ |
|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | 0.25 [-0.27..0.73] | 1.86 [1.30..2.24] | 2.11 [1.97..2.61] | -1.11 [-671.55..-0.22] | 2.63 [2.46..2.98] | 1.52 [-668.57..2.24] | tidak dapat dibedakan pada pengukuran ini | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M1-50rps** | 0.44 [0.36..0.66] | 1.75 [1.60..3.27] | 2.19 [1.96..3.93] | 0.11 [-55.35..0.37] | 3.51 [3.30..334.31] | 3.62 [-51.84..334.68] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M1-100rps** | 0.73 [0.34..0.34] | 70.87 [1.32..1.32] | 71.60 [1.66..1.66] | 138.82 [42.68..42.68] | 2,162.14 [-34.88..-34.88] | 2,300.96 [7.80..7.80] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M2-20rps** | 0.40 [0.26..0.55] | 1.70 [1.21..2.05] | 2.10 [1.76..2.31] | -201.85 [-9,186.16..0.14] | 2.64 [2.22..2.91] | -199.21 [-9,183.94..3.05] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **M2-50rps** | -0.72 [-0.90..1.40] | 2.48 [1.65..2.48] | 1.76 [1.58..3.41] | -0.23 [-0.23..5.48] | 6.64 [4.39..678.45] | 6.41 [5.43..683.93] | tidak dapat dibedakan pada pengukuran ini | tidak dapat dibedakan pada pengukuran ini | rentang p50 tidak tumpang tindih |
| **J1-50rps** | 0.81 [0.80..0.82] | 2.20 [2.07..2.29] | 3.01 [2.88..3.09] | 1.37 [1.32..1.56] | 2.97 [2.75..3.51] | 4.34 [4.31..4.83] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **J1-200rps** | 0.61 [0.56..0.71] | 1.74 [1.63..1.95] | 2.35 [2.21..2.59] | 1.03 [0.99..1.47] | 3.52 [2.68..5.24] | 4.55 [4.15..6.34] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K1-20rps** | 0.43 [0.22..0.69] | 2.23 [1.78..2.44] | 2.66 [2.47..2.66] | 1.25 [1.22..1.51] | 2.59 [2.05..3.41] | 3.84 [3.56..4.66] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K1-50rps** | 0.77 [0.46..0.94] | 2.78 [2.63..4.29] | 3.55 [3.17..5.23] | 2.28 [1.67..6.04] | 22.16 [-125.93..3,037.11] | 24.44 [-119.89..3,041.07] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K2-5rps** | 3.90 [3.90..3.90] | 3,269.78 [3,269.78..3,269.78] | 3,273.68 [3,273.68..3,273.68] | 13.98 [13.98..13.98] | 3,335.80 [3,335.80..3,335.80] | 3,349.78 [3,349.78..3,349.78] | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih | rentang p50 tidak tumpang tindih |
| **K2-10rps** | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

---

## 3. Median CPU dan Memori per Container pada Fase Ukur (Dua Tabel Terpisah)

Nilai adalah **median** sampel `docker stats` pada jendela fase ukur 30 detik (bukan puncak), lalu median antar-ulangan. `100%` CPU = 1 core logis penuh. Kolom `superapp-nginx-noauth` hanya terisi pada jalur `noauth`.

### 3.1. Median CPU (%) per Container

| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |
|---|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | `direct` | 0.00 | 0.00 | 0.16 | 9.91 | 1.64 | 0.16 | 0.00 | 0.01 | 0.17 |
| **M1-20rps** | `noauth` | 0.00 | 1.06 | 0.16 | 9.12 | 1.42 | 0.16 | 0.00 | 0.00 | 0.17 |
| **M1-20rps** | `gateway` | 1.69 | 0.00 | 3.17 | 9.46 | 1.43 | 0.16 | 0.00 | 0.00 | 0.17 |
| **M1-50rps** | `direct` | 0.00 | 0.00 | 0.15 | 20.36 | 3.26 | 0.15 | 0.00 | 0.02 | 0.16 |
| **M1-50rps** | `noauth` | 0.00 | 2.43 | 0.15 | 21.13 | 3.20 | 0.15 | 0.00 | 0.00 | 0.16 |
| **M1-50rps** | `gateway` | 3.66 | 0.00 | 7.44 | 20.05 | 3.06 | 0.14 | 0.00 | 0.00 | 0.16 |
| **M1-100rps** | `direct` | 0.00 | 0.00 | 0.14 | 36.99 | 6.40 | 0.13 | 0.00 | 0.00 | 0.14 |
| **M1-100rps** | `noauth` | 0.00 | 4.72 | 0.15 | 41.83 | 6.26 | 0.14 | 0.00 | 0.00 | 0.15 |
| **M1-100rps** | `gateway` | 7.80 | 0.00 | 24.72 | 51.35 | 5.46 | 0.14 | 0.00 | 0.00 | 0.16 |
| **M2-20rps** | `direct` | 0.00 | 0.00 | 0.17 | 8.10 | 1.22 | 0.16 | 0.00 | 0.01 | 0.17 |
| **M2-20rps** | `noauth` | 0.00 | 1.06 | 0.16 | 8.01 | 1.13 | 0.16 | 0.00 | 0.00 | 0.17 |
| **M2-20rps** | `gateway` | 1.64 | 0.00 | 3.41 | 8.06 | 1.11 | 0.16 | 0.00 | 0.01 | 0.17 |
| **M2-50rps** | `direct` | 0.00 | 0.00 | 0.20 | 24.40 | 3.77 | 0.18 | 0.00 | 0.01 | 0.19 |
| **M2-50rps** | `noauth` | 0.00 | 2.43 | 0.16 | 19.08 | 2.78 | 0.15 | 0.00 | 0.00 | 0.17 |
| **M2-50rps** | `gateway` | 4.16 | 0.00 | 9.96 | 22.22 | 3.02 | 0.17 | 0.00 | 0.02 | 0.17 |
| **J1-50rps** | `direct` | 0.00 | 0.00 | 0.20 | 0.17 | 0.00 | 5.74 | 0.00 | 0.01 | 0.21 |
| **J1-50rps** | `noauth` | 0.00 | 3.21 | 0.19 | 0.17 | 0.00 | 7.79 | 0.00 | 0.00 | 0.22 |
| **J1-50rps** | `gateway` | 5.19 | 0.00 | 10.88 | 0.17 | 0.00 | 7.08 | 0.00 | 0.00 | 0.19 |
| **J1-200rps** | `direct` | 0.00 | 0.00 | 0.18 | 0.18 | 0.00 | 19.31 | 0.00 | 0.01 | 0.20 |
| **J1-200rps** | `noauth` | 0.00 | 10.74 | 0.16 | 0.15 | 0.00 | 25.16 | 0.00 | 0.01 | 0.18 |
| **J1-200rps** | `gateway` | 15.53 | 0.00 | 35.46 | 0.15 | 0.00 | 24.67 | 0.00 | 0.00 | 0.19 |
| **K1-20rps** | `direct` | 0.00 | 0.00 | 0.21 | 0.20 | 0.00 | 0.21 | 9.85 | 0.02 | 0.23 |
| **K1-20rps** | `noauth` | 0.00 | 1.42 | 0.21 | 0.18 | 0.00 | 0.20 | 10.20 | 0.00 | 0.22 |
| **K1-20rps** | `gateway` | 2.13 | 0.00 | 4.62 | 0.18 | 0.00 | 0.20 | 9.28 | 0.01 | 0.21 |
| **K1-50rps** | `direct` | 0.00 | 0.00 | 0.21 | 0.17 | 0.00 | 0.21 | 19.76 | 0.01 | 0.23 |
| **K1-50rps** | `noauth` | 0.00 | 3.38 | 0.20 | 0.18 | 0.00 | 0.20 | 19.07 | 0.00 | 0.24 |
| **K1-50rps** | `gateway` | 6.02 | 0.00 | 11.65 | 0.20 | 0.00 | 0.22 | 33.71 | 0.00 | 0.22 |
| **K2-5rps** | `direct` | 0.00 | 0.00 | 0.20 | 0.18 | 0.00 | 0.21 | 5.62 | 0.00 | 0.23 |
| **K2-5rps** | `noauth` | 0.00 | 0.48 | 0.21 | 0.18 | 0.00 | 0.23 | 6.18 | 0.02 | 0.24 |
| **K2-5rps** | `gateway` | 0.00 | 0.00 | 203.01 | 0.35 | 0.01 | 0.29 | 201.62 | 173.12 | 0.38 |
| **K2-10rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

### 3.2. Median Memori (MiB) per Container

| Kondisi | Jalur | `nginx` | `superapp-nginx-noauth` | `auth-verifier` | `microcred-api` | `db` | `judul-api` | `matkul` | `pocketbase` | `redis` |
|---|---|---|---|---|---|---|---|---|---|---|
| **M1-20rps** | `direct` | 13.6 | 7.4 | 49.4 | 109.6 | 60.0 | 53.0 | 213.4 | 18.0 | 16.7 |
| **M1-20rps** | `noauth` | 13.7 | 7.8 | 49.4 | 109.5 | 60.3 | 53.0 | 213.4 | 18.0 | 16.6 |
| **M1-20rps** | `gateway` | 14.0 | 7.4 | 49.5 | 109.5 | 60.2 | 53.0 | 213.4 | 17.8 | 16.6 |
| **M1-50rps** | `direct` | 13.7 | 7.5 | 51.5 | 110.1 | 56.0 | 53.0 | 213.4 | 18.0 | 16.7 |
| **M1-50rps** | `noauth` | 13.7 | 8.0 | 49.4 | 109.8 | 56.0 | 53.0 | 213.4 | 18.0 | 16.6 |
| **M1-50rps** | `gateway` | 14.3 | 7.5 | 51.7 | 109.8 | 56.0 | 53.0 | 213.4 | 18.0 | 16.6 |
| **M1-100rps** | `direct` | 13.7 | 7.5 | 51.5 | 111.0 | 56.0 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M1-100rps** | `noauth` | 13.8 | 8.3 | 51.5 | 110.8 | 56.0 | 53.0 | 213.5 | 18.2 | 16.6 |
| **M1-100rps** | `gateway` | 15.4 | 7.5 | 58.4 | 110.8 | 63.1 | 53.0 | 213.4 | 18.2 | 16.6 |
| **M2-20rps** | `direct` | 13.8 | 7.5 | 53.3 | 110.7 | 66.5 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M2-20rps** | `noauth` | 13.8 | 7.8 | 53.3 | 110.7 | 66.5 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M2-20rps** | `gateway` | 14.1 | 7.5 | 53.4 | 110.7 | 66.5 | 53.0 | 213.5 | 18.2 | 16.7 |
| **M2-50rps** | `direct` | 13.7 | 7.5 | 53.3 | 110.8 | 66.0 | 53.0 | 214.2 | 18.2 | 16.7 |
| **M2-50rps** | `noauth` | 13.7 | 8.0 | 53.3 | 110.7 | 65.9 | 53.0 | 213.6 | 18.2 | 16.6 |
| **M2-50rps** | `gateway` | 14.4 | 7.5 | 53.5 | 110.7 | 65.9 | 53.0 | 214.2 | 18.2 | 16.6 |
| **J1-50rps** | `direct` | 13.8 | 7.5 | 53.3 | 110.6 | 66.0 | 53.4 | 214.3 | 18.3 | 16.7 |
| **J1-50rps** | `noauth` | 13.7 | 8.0 | 53.3 | 110.6 | 66.0 | 53.3 | 214.3 | 18.4 | 16.6 |
| **J1-50rps** | `gateway` | 14.3 | 7.5 | 53.5 | 110.6 | 66.0 | 53.3 | 214.3 | 18.3 | 16.6 |
| **J1-200rps** | `direct` | 13.8 | 7.5 | 53.3 | 110.6 | 66.0 | 54.0 | 214.3 | 18.4 | 16.7 |
| **J1-200rps** | `noauth` | 13.7 | 8.8 | 53.3 | 110.6 | 66.0 | 54.0 | 214.2 | 18.5 | 16.6 |
| **J1-200rps** | `gateway` | 15.1 | 7.5 | 55.6 | 110.6 | 66.0 | 53.9 | 214.2 | 18.6 | 16.6 |
| **K1-20rps** | `direct` | 13.7 | 7.5 | 55.3 | 110.6 | 66.0 | 53.8 | 246.2 | 18.5 | 16.7 |
| **K1-20rps** | `noauth` | 13.7 | 7.8 | 55.3 | 110.6 | 66.0 | 53.8 | 255.4 | 18.5 | 16.7 |
| **K1-20rps** | `gateway` | 14.1 | 7.5 | 55.4 | 110.6 | 66.0 | 53.8 | 262.3 | 18.5 | 16.6 |
| **K1-50rps** | `direct` | 13.8 | 7.5 | 55.3 | 110.6 | 66.0 | 53.8 | 263.0 | 18.6 | 16.7 |
| **K1-50rps** | `noauth` | 13.7 | 8.0 | 55.3 | 110.6 | 66.0 | 53.8 | 273.1 | 18.5 | 16.6 |
| **K1-50rps** | `gateway` | 14.3 | 7.5 | 53.6 | 110.6 | 66.0 | 53.8 | 267.0 | 18.5 | 16.6 |
| **K2-5rps** | `direct` | 13.7 | 7.5 | 55.3 | 110.6 | 66.0 | 53.8 | 297.2 | 18.8 | 16.7 |
| **K2-5rps** | `noauth` | 13.8 | 7.7 | 55.3 | 110.6 | 66.0 | 53.8 | 297.2 | 18.8 | 16.7 |
| **K2-5rps** | `gateway` | 13.8 | 7.5 | 55.4 | 110.6 | 66.0 | 53.8 | 230.9 | 19.0 | 16.7 |
| **K2-10rps** | `direct` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `noauth` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |
| **K2-10rps** | `gateway` | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur | tidak diukur |

