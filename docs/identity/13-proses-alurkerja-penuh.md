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
    R --> T[Tinjau<br/>DPA di Ruang dosen]
    T -- setuju --> K[Kirim dan catat] --> E([Disetujui])
    T -- revisi --> V[Revisi<br/>worker] --> T
```

| Langkah | Siapa | Dikerjakan |
|---|---|---|
| Unggah KHS | mahasiswa | identity menyelesaikannya atas nama mahasiswa saat `POST /pengajuan` (assignee `${initiator}` = akun layanan) |
| Baca KHS | worker → matkul `extract-khs` | membaca PDF, ekstraksi LLM (atau pakai hasil bacaan pratinjau untuk berkas yang sama), hitung keyakinan, simpan |
| Periksa | mahasiswa | di layar pengajuan; identity menyelesaikan tugas saat mahasiswa menekan "Data sudah benar" |
| Rekomendasi | worker → matkul `recommend` | LLM dengan panduan prodi; batas SKS prodi; peringatan dari data |
| Tinjau | DPA | halaman `/dosen` aplikasi (atau Tasklist AlurKerja); assignee = email DPA (`dosen_pa`); keluaran `keputusan`, `catatan_dosen` |
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
2. Form tugas "Tinjau & putuskan": keluaran **`keputusan`** (radio `setuju` / `revisi`, wajib) dan **`catatan_dosen`** (teks, wajib bila revisi). Nama harus persis itu. Form ini hanya diperlukan bila dosen juga memakai Tasklist; halaman `/dosen` mengirim variabel yang sama. Form sama dengan proses StudentGateway.
3. Akun dosen di identity memakai email yang sama dengan akun AlurKerja-nya (id pengguna Camunda = email huruf kecil).
4. Akun layanan (`initiator`) perlu ada di AlurKerja; tugas mahasiswa diselesaikan atas namanya lewat REST.

Agar tugas terlihat di **Tasklist** AlurKerja (selesai disiapkan 26 Nov 2026):

- Deploy lewat Studio (Drive, unggah BPMN, buat form, **Deploy > Live**, hanya Owner). Deploy lewat REST saja tidak terdaftar di Studio.
- Deploy Live masuk ke tenant ber-UUID milik lingkungan Live, bukan `studentgateway`; isi `ALURKERJA_TENANT_ID` di `services/identity/.env` dengan UUID itu (lihat `GET /engine-rest/process-definition`).
- Form disimpan di Studio, bukan di berkas `.bpmn`: setelah impor ulang, buat atau tempel lagi.
- Rangkuman di atas keputusan: komponen **Rich Text From Variable** pada form Tinjau, sumber `ringkasan_dosen` (HTML buatan matkul, maks. 3900 karakter). Komponen itu hanya menawarkan variabel yang menjadi field di form langkah lain, jadi form tugas Periksa memuat field Rich Text berkunci `ringkasan_dosen`.
- Analytics (Studio > Analytics): tiga dashboard, satu per tab di web. Semua pertanyaan SQL berawalan `Superapp -`, tidak memuat nama mahasiswa, dan tidak menghitung pengajuan yang dibatalkan. Hanya memuat instans lingkungan Live. Tersimpan di Studio, tidak di repo.

| Tab web | Dashboard di Studio (id lokal) | Isi |
|---|---|---|
| Ringkasan | Dashboard Kaprodi - Ringkasan (4) | rencana dan judul: diajukan, disetujui, menunggu; tema judul terbanyak |
| Mata Kuliah | Dashboard Kaprodi - Mata Kuliah (2) | 8 kartu dari `<<perencanaan-studi-superapp>>` |
| Judul Tugas Akhir | Dashboard Kaprodi - Judul Tugas Akhir (3) | diajukan, disetujui, rata-rata revisi, tema terbanyak, tema per prodi dari `<<pengajuan-judul-superapp>>` |

- Cerminan di web: halaman **`/dosen/analitik`** (kaprodi) memanggil identity `GET /analitik/dashboard?tab=ringkasan|matkul|judul`, yang membaca susunan dashboard dan menjalankan tiap pertanyaan lewat API laporan AlurKerja (`/api/v1/report/{tenant}/dashboard/{id}/app` dan `/question/{id}/execute-query`) memakai Auth Token integrasi. Aktif bila `ALURKERJA_AUTH_TOKEN_SLUG`, `ALURKERJA_CLIENT_ID`, `ALURKERJA_CLIENT_SECRET`, dan `ALURKERJA_DASHBOARD_RINGKASAN` / `_MATKUL` / `_JUDUL` terisi di `services/identity/.env` (dashboard harus **Published**). Perubahan di Studio ikut tampil (angka, tabel, batang, garis; jenis lain sebagai tabel). SQL tidak diteruskan ke browser. Datanya rekap **seluruh prodi**: pembatasan per prodi memerlukan parameter pada pertanyaan (belum dibuat). API itu tidak terdokumentasi publik, jadi bisa berubah saat AlurKerja diperbarui.

## Terbukti di AlurKerja lokal (26 Nov 2026)

Satu pengajuan data uji dijalankan lewat gateway dengan AlurKerja, worker, matkul, dan LLM sungguhan (tenant `studentgateway`): mulai proses, `Task_Unggah`, baca KHS (keyakinan 0,7), `Task_Periksa`, rekomendasi, tinjauan DPA (minta revisi), revisi, tinjauan kedua (setuju), selesai. Status proses `COMPLETED`, tanpa insiden, dan nama mahasiswa tidak ada di variabel proses. Sebelum bisa di-deploy, `textAnnotation`/`association` di BPMN harus dipindah ke bawah `sequenceFlow`.

Revisi dengan catatan yang **hanya** membatasi SKS (mis. "Maksimal 18 SKS") dihitung tanpa pilihan LLM: rencana sebelumnya diisi sampai batas (uji kedua: tepat 18 SKS; sebelum perbaikan 9 SKS). Catatan lain tetap disusun LLM, lalu dipangkas bila melebihi batas. Pada uji kedua, satu panggilan revisi gagal karena sambungan (`fetch failed`) dan berhasil saat diulang setelah kunci tugas habis (sekitar 2 menit).

Kegagalan langkah AI dicoba 3 kali (jeda 30 detik) sebelum menjadi insiden. Terbukti di AlurKerja lokal dengan PDF rusak: tiga percobaan dalam sekitar 65 detik, lalu `pesan_galat` "500 Invalid PDF structure" tampil pada pengajuan dan pembatalan berhasil.

Worker melaporkan kegagalan ke `/external-task/{id}/failure` (sebelumnya `/fail`, yang dijawab 404 sehingga insiden tidak pernah tercatat). Pembacaan PDF di matkul mencoba dua kali lalu memakai `pdftotext`.

## Yang belum terbukti

- Pemindahan DPA saat pengajuan berjalan pada AlurKerja sungguhan.
- Form Tasklist di Studio (aplikasi memakai halaman `/dosen`).
- AlurKerja selain instalasi lokal ini.

## Perilaku yang perlu diketahui

- Wizard rekomendasi di frontend (hasil instan sebelum mengajukan) tetap ada sebagai **pratinjau**. Saat mengajukan, berkas KHS yang sama dikirim ke proses di server. **Bacaan** dan **rencana** pratinjau disimpan server dan dipakai apa adanya (tabel `matkul_bacaan` dan `matkul_pratinjau`, kunci SHA-256 isi berkas, NIM, panduan, dan semester; disimpan 7 hari), sehingga tidak ada pemanggilan LLM kedua dan langkah Periksa dilewati. Nilai yang diubah mahasiswa di wizard dicatat sebagai peringatan "Perlu dicek" untuk pembimbing. Rencana disusun baru bila pratinjau tidak ada (kedaluwarsa, panduan berganti, NIM akun kosong) dan pada setiap revisi; revisi memakai nilai dari berkas KHS, bukan nilai yang diubah. Kegiatan non-mata kuliah dan target akademik hanya ada di pratinjau.
- Per pengajuan, LLM membaca KHS dan menyusun rekomendasi satu kali (saat pratinjau); revisi memanggil LLM lagi.
- Worker lama StudentGateway dan worker superapp boleh berjalan bersamaan (topik berbeda).

## Antarmuka dosen (`/dosen`)

Tugas "Tinjau" dikerjakan di layar aplikasi sendiri; Tasklist AlurKerja tetap bisa dipakai karena nama variabelnya sama.

```
Layar dosen → POST /pengajuan/{id}/keputusan → identity memeriksa hak → engine-rest: complete Task_Tinjau
```

- Identity hanya mengizinkan DPA yang ditugaskan (atau superadmin), pada tahap `tinjau`. Catatan wajib untuk revisi. `catatan_dosen` selalu dikirim (kosong bila tidak diisi) supaya catatan lama tidak tertinggal.
- AlurKerja gagal → HTTP 502, tidak ada yang berubah. Tugas sudah tidak terbuka → 409.
- Penyelesaian memakai akun layanan (Basic Auth), jadi riwayat AlurKerja mencatat akun layanan; dosen yang memutuskan tercatat di audit identity.
- API tasklist AlurKerja (`direct-complete`, Bearer token) **belum dipakai**: cara dosen memperoleh token belum terdokumentasi.
- Daftar tugas dosen berasal dari `GET /pengajuan?dpa_id=…`, bukan dari AlurKerja. Server hanya menyinkronkan 20 pengajuan terbuka terbaru per permintaan daftar.

| Menu | Peran | Isi |
|---|---|---|
| Perlu ditinjau, Mahasiswa bimbingan, Riwayat keputusan | `dosen_pa` | antrean, detail rencana, setujui atau minta revisi |
| Pengajuan prodi | `kaprodi` | pemantauan saja; BPMN tidak punya tugas untuk kaprodi |

Dosen dan kaprodi yang bukan mahasiswa diarahkan ke `/dosen` setelah masuk. Kode: `frontend/app/dosen`, `frontend/components/dosen`, `frontend/src/services/dosen-service.ts`.
