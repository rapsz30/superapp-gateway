# AlurKerja Connector (superapp)

Worker **External Task** untuk proses `perencanaan-studi-superapp`. Ia menarik tugas langkah AI dari AlurKerja (Camunda 7),
memanggil endpoint `/api/matkul/*` di layanan matkul, lalu menyelesaikan atau menggagalkan tugas. Disalin dari
`alurkerja-connector` StudentGateway dengan beberapa penyederhanaan; penjelasan lengkap di
[docs/identity/13](../docs/identity/13-proses-alurkerja-penuh.md).

| Topik (di BPMN) | Endpoint matkul |
|---|---|
| `superapp-ekstraksi-khs` | `POST /api/matkul/extract-khs` (`khs_file_id`, `semester_target`, `id_pengajuan`) |
| `superapp-rekomendasi-matkul` | `POST /api/matkul/recommend` (`khs_ref`, `semester_target`) |
| `superapp-revisi-rencana` | `POST /api/matkul/revise` (`rencana_ref`, `catatan_dosen`) |

- **Topik berawalan** `TOPIC_PREFIX` (compose: `superapp-`) dan **filter proses** `ALURKERJA_PROCESS_NAME`, supaya tidak berebut tugas
  dengan worker StudentGateway yang lama.
- **Autentikasi:** Basic Auth akun Camunda ke AlurKerja; `Bearer GATEWAY_TOKEN` (= `MATKUL_SERVICE_TOKEN`) ke matkul.
- Log hanya memuat durasi dan status per tugas, tanpa isi variabel (tidak mencetak data mahasiswa).
- Tugas yang gagal diberi `retries: 0` sehingga muncul sebagai insiden Camunda; identity menampilkannya sebagai `pesan_galat` pada pengajuan.

## Menjalankan

```powershell
Copy-Item .env.example .env          # isi ALURKERJA_ET_USERNAME/PASSWORD dan GATEWAY_TOKEN
npm install
npm test                             # tes dengan server tiruan (tanpa AlurKerja)
npm run dev                          # worker (butuh GATEWAY_URL, TOPIC_PREFIX, ALURKERJA_PROCESS_NAME di lingkungan)
```

Dalam Docker Compose, layanan `alurkerja-connector` mengisi `GATEWAY_URL`, `TOPIC_PREFIX`, dan `ALURKERJA_PROCESS_NAME` sendiri.
Untuk AlurKerja lokal bersertifikat mkcert, salin root CA ke `certs/rootCA.pem` (tidak di-commit).
