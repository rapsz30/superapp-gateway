# 13. Proses AlurKerja Lengkap, Connector, dan Langkah AI di Matkul

Pilihan "B": AlurKerja mengorkestrasi **seluruh** proses perencanaan studi, termasuk langkah AI ("AI di dalam task"), seperti desain asli StudentGateway. Connector dan BPMN dipindahkan ke repo ini.

## Apa yang dipindahkan dari `program` / `alurkerja-connector`

| Komponen | Asal | Sekarang di superapp | Perubahan |
|---|---|---|---|
| BPMN | `alurkerja-connector/bpmn/perencanaan-studi-semester.bpmn` | [`alurkerja/perencanaan-studi-superapp.bpmn`](../../alurkerja/perencanaan-studi-superapp.bpmn) | kunci proses `perencanaan-studi-superapp`; topik berawalan `superapp-`. Alur dan variabel sama |
| Worker | `alurkerja-connector/` | [`alurkerja-connector/`](../../alurkerja-connector/README.md) | autentikasi disederhanakan ke Basic Auth Camunda; klien chatbot (`direct-start`) dibuang karena identity yang memulai proses; `TOPIC_PREFIX`; filter `processDefinitionKey`; meneruskan `id_pengajuan` |
| Endpoint langkah AI | `program/app/api/matkul/{upload,extract-khs,recommend,revise}` | `services/matkul/app/api/matkul/*` | basis data matkul sendiri (`matkul-db`); autentikasi token layanan; panduan per prodi dari identity |
| Logika rekomendasi | `program/src/lib/{recommend,rencana}.ts` | `services/matkul/src/lib/proses/` | disalin apa adanya; batas SKS kini mengikuti prodi |

Kunci proses dan topik dibedakan **sengaja**: worker StudentGateway yang lama (tanpa filter) akan mengambil tugas apa pun dengan topik yang sama. Dengan topik `superapp-*`, dua worker bisa hidup bersamaan tanpa berebut.

## Alur BPMN

```mermaid
flowchart LR
    S([Mulai]) --> U[Unggah KHS<br/>mahasiswa, otomatis]
    U --> B[Baca KHS<br/>worker]
    B --> G{keyakinan ≥ 0,9?}
    G -- ya --> R[Rekomendasi<br/>worker]
    G -- tidak --> P[Periksa<br/>mahasiswa]
    P --> R
    R --> T[Tinjau<br/>DPA di Tasklist]
    T -- setuju --> K[Kirim dan catat] --> E([Disetujui])
    T -- revisi --> V[Revisi<br/>worker] --> T
```

| Langkah | Siapa | Dikerjakan |
|---|---|---|
| Unggah KHS | mahasiswa | identity menyelesaikannya atas nama mahasiswa saat `POST /pengajuan` (assignee `${initiator}` = akun layanan) |
| Baca KHS | worker → matkul `extract-khs` | membaca PDF, ekstraksi LLM, hitung keyakinan, simpan |
| Periksa | mahasiswa | di layar pengajuan; identity menyelesaikan tugas saat mahasiswa menekan "Data sudah benar" |
| Rekomendasi | worker → matkul `recommend` | LLM dengan panduan prodi; batas SKS prodi; peringatan dari data |
| Tinjau | DPA | Tasklist AlurKerja; assignee = email DPA (`dosen_pa`); keluaran `keputusan`, `catatan_dosen` |
| Revisi | worker → matkul `revise` | LLM menyesuaikan rencana dengan catatan dosen |
| Kirim rencana, catat ke laporan prodi, pengingat 2 hari | AlurKerja | masih `${true}` (penanda tempat), sama seperti BPMN asalnya |

### Variabel proses

Dimasukkan identity saat memulai: `dosen_pa` (email, huruf kecil), `initiator`, `nim_mahasiswa`, `id_pengajuan`, `khs_file_id`, `semester_target`, `program_studi`, `versi_panduan`. Diisi worker: `khs_ref`, `ipk`, `sks_lulus`, `mk_lulus`, `mk_ulang`, `keyakinan`, `prodi`, `nim_cocok`, `rencana_ref`, `rencana_mk`, `total_sks`, `alasan`, `peringatan`, `ada_peringatan`, `jumlah_revisi`. Diisi dosen: `keputusan`, `catatan_dosen`. **Nama mahasiswa tidak pernah masuk ke AlurKerja.** Data KHS lengkap (nama, NIM, nilai per mata kuliah) hanya di `matkul-db`.

## Panduan per prodi di dalam proses

`extract-khs` menerima `id_pengajuan` dan memanggil identity `GET /internal/pengajuan/{id}/konteks` (header `X-Internal-Token`) untuk mendapatkan prodi, NIM akun, batas SKS prodi, dan **panduan aktif**. Teks panduan **disimpan bersama KHS** di matkul; `recommend` dan semua `revise` untuk KHS itu membaca dari sana. Akibatnya satu pengajuan memakai satu versi panduan dari awal sampai disetujui, walau kaprodi mengaktifkan versi baru di tengah jalan. Versi itu dicatat di pengajuan.

**Batas SKS:** nilai 24 yang tertanam di kode asal adalah angka panduan Informatika. Kini ada `prodi.maks_sks_semester` (1–40; kosong = bawaan 24) yang diatur superadmin lewat `PATCH /prodi/{id}` dan dipakai saat memangkas rencana. Catatan dosen ("maksimal 18 SKS") tetap boleh menurunkan batas, tidak pernah menaikkannya.

## KHS milik orang lain

NIM yang dibaca dari KHS dibandingkan NIM akun. Bila berbeda, `keyakinan` dipaksa 0 dan `nim_cocok = false`, sehingga proses berhenti di "Periksa" dan **tidak pernah sampai ke dosen** sebagai rencana orang yang salah. Layar menampilkan peringatan; satu-satunya tindakan adalah membatalkan.

## Keamanan layanan-ke-layanan

| Hubungan | Perlindungan |
|---|---|
| connector → matkul `/api/matkul/*` | `Authorization: Bearer MATKUL_SERVICE_TOKEN` (perbandingan waktu-konstan; 503 bila token belum diatur). JWT pengguna **tidak** diterima di sini |
| identity → matkul `upload` | token layanan yang sama |
| matkul → identity `/internal/*` | `X-Internal-Token` = `INTERNAL_TOKEN`; NGINX menjawab 404 untuk `/api/identity/internal/*` dari luar |
| connector → AlurKerja | Basic Auth akun Camunda |
| identity → AlurKerja | Basic Auth akun Camunda |

Gateway tidak punya rute khusus untuk `/api/matkul/*`, tetapi aturan umum `/api/matkul-recommender/x` → `/api/x` membuat `/api/matkul-recommender/matkul/extract-khs` secara teknis sampai ke matkul. Tanpa token layanan jawabannya 401, sehingga tidak bisa dipakai pengguna.

## Menjalankan

```powershell
# 1. Isi rahasia (nilainya harus cocok antar berkas)
Copy-Item services\matkul\.env.example services\matkul\.env.local         # MATKUL_SERVICE_TOKEN, INTERNAL_TOKEN, POSTGRES_*, DATABASE_URL, OPENAI_API_KEY
Copy-Item services\identity\.env.example services\identity\.env           # MATKUL_SERVICE_TOKEN, INTERNAL_TOKEN, JWT_SECRET, ALURKERJA_*
Copy-Item alurkerja-connector\.env.example alurkerja-connector\.env       # GATEWAY_TOKEN (= MATKUL_SERVICE_TOKEN), ALURKERJA_ET_*
Copy-Item "$env:LOCALAPPDATA\mkcert\rootCA.pem" alurkerja-connector\certs\rootCA.pem   # bila AlurKerja lokal memakai mkcert

# 2. Jalankan
docker compose up -d --build
```

| Rahasia | Harus sama di |
|---|---|
| `MATKUL_SERVICE_TOKEN` | `services/matkul/.env.local`, `services/identity/.env`, `GATEWAY_TOKEN` di `alurkerja-connector/.env` |
| `INTERNAL_TOKEN` | `services/identity/.env` (dibaca juga verifier) dan `services/matkul/.env.local` |
| akun Camunda | `ALURKERJA_USERNAME/PASSWORD` di identity dan `ALURKERJA_ET_USERNAME/PASSWORD` di connector |

### Menyiapkan AlurKerja (sekali)

1. Impor [`perencanaan-studi-superapp.bpmn`](../../alurkerja/perencanaan-studi-superapp.bpmn) di AlurKerja Studio dan deploy ke tenant yang dipakai (isi `ALURKERJA_TENANT_ID` bila multi-tenant).
2. Form tugas "Tinjau & putuskan": keluaran **`keputusan`** (radio `setuju` / `revisi`, wajib) dan **`catatan_dosen`** (teks, wajib bila revisi). Nama harus persis itu. Form ini sama dengan yang dipakai proses StudentGateway.
3. Akun dosen di identity memakai email yang sama dengan akun AlurKerja-nya (id pengguna Camunda = email huruf kecil).
4. Akun layanan (`initiator`) perlu ada di AlurKerja; tugas mahasiswa diselesaikan atas namanya lewat REST.

## Yang belum terbukti

Diuji dengan komponen sungguhan kecuali **Camunda/AlurKerja**, yang ditiru oleh server HTTP tiruan yang menjalankan urutan BPMN. Belum terbukti di AlurKerja Anda:
- BPMN hasil salinan dapat dideploy dan dimulai (`startEvent` hingga `Task_Unggah`), dan akun layanan boleh menyelesaikan tugas milik `${initiator}`.
- `engine-rest` menerima: `process-definition/key/.../tenant-id/.../start`, `history/activity-instance?unfinished=true`, `history/variable-instance`, `incident`, `task?taskDefinitionKey=`, dan `PUT process-instance/{id}/variables/dosen_pa` pada tenant Anda.
- Form Studio mengisi `keputusan` dan `catatan_dosen` dengan nama yang benar.
- Variabel bertipe String berisi JSON yang dikirim worker (`rencana_mk`, `mk_ulang`, `peringatan`) terbaca utuh dari riwayat variabel (identity mengurainya).

Coba satu pengajuan dari awal sampai disetujui di lingkungan AlurKerja sebelum dipakai.

## Perilaku yang perlu diketahui

- Wizard rekomendasi di frontend (hasil instan sebelum mengajukan) tetap ada sebagai **pratinjau**. Saat mengajukan, KHS asli diunggah ulang dan dihitung ulang oleh proses di server, jadi hasil resmi bisa sedikit berbeda dari pratinjau (LLM tidak deterministik, dan pratinjau memakai nilai yang sudah diedit mahasiswa).
- Langkah AI memakai LLM dua kali per pengajuan (pratinjau dan proses).
- Worker lama StudentGateway dan worker superapp boleh berjalan bersamaan (topik berbeda).
