# 02. Kontrak API

Semua rute di bawah `/api/identity` (lewat `apiFetch`), wajib token. Galat berbentuk `{ "detail": "..." }` (422: `detail` berupa daftar galat validasi). Sumber kebenaran: `services/identity/src/api/routes/judul.py`.

## Tipe

```ts
type Orang = { id: string; nama_lengkap: string; nim: string | null }

type Referensi = { sitasi: string; link: string }          // link wajib http(s)

type Rekomendasi = {
  judul: string
  tema: string
  deskripsi: string
  metodologi: string                                       // satu tahap per baris
  keywords: string[]
  referensi: Referensi[]
}

type PengajuanJudul = {
  id: string
  status: 'diajukan' | 'disetujui' | 'dibatalkan'
  tahap: 'tinjau' | 'perbaikan' | 'selesai'
  mode: 'alurkerja' | 'lokal'
  topik: string
  judul: string
  tema: string
  deskripsi: string
  metodologi: string
  keywords: string[]
  referensi: Referensi[]
  catatan: string | null                                   // catatan pembimbing / alasan batal
  jumlah_revisi: number
  mahasiswa: Orang | null
  pembimbing: Orang | null
  prodi: { id: string; kode: string; nama: string } | null
  diajukan_pada: string
  diputuskan_pada: string | null
}
```

Isi kiriman (`JudulIn`): `topik` ≤ 300 (boleh kosong), `judul` 10–300, `tema` (dari daftar), `deskripsi` 20–2000, `metodologi` ≤ 3000, `keywords` ≤ 10 (masing-masing ≤ 60), `referensi` ≤ 10 (`sitasi` ≤ 600). Properti lain ditolak.

## Mahasiswa

| Method | Rute | Isi | Hasil |
|---|---|---|---|
| GET | `/judul/tema` | — | `{ data: string[] }` (semua peran) |
| GET | `/judul/saya` | — | `{ pembimbing: Orang \| null, pengajuan: PengajuanJudul \| null, riwayat: { id, topik, dibuat, rekomendasi: Rekomendasi[] }[] }` (riwayat ≤ 10, terbaru dulu; `pengajuan` = yang terakhir, apa pun statusnya) |
| POST | `/judul/rekomendasi` | `{ minat }` (3–300) | `{ id, topik, rekomendasi: Rekomendasi[], memakai_nilai: boolean }` — butuh 5–40 detik; 502 bila AI gagal |
| POST | `/pengajuan-judul` | `JudulIn` | 201 `PengajuanJudul`; 409 tanpa pembimbing atau masih ada yang terbuka |
| PUT | `/pengajuan-judul/{id}` | `JudulIn` | hanya saat `tahap = perbaikan`; selain itu 409 |
| POST | `/pengajuan-judul/{id}/batalkan` | — | `PengajuanJudul` |

## Pembimbing dan daftar

| Method | Rute | Isi | Akses / hasil |
|---|---|---|---|
| GET | `/pengajuan-judul?status=&pembimbing_id=&halaman=&ukuran=` | — | `{ data, total }`; mahasiswa miliknya, pembimbing bimbingannya, kaprodi prodinya |
| GET | `/pengajuan-judul/{id}` | — | `PengajuanJudul`; 404 di luar cakupan |
| POST | `/pengajuan-judul/{id}/keputusan` | `{ keputusan: 'setuju'\|'revisi', catatan? }` (≤ 1000) | pembimbing yang ditunjuk atau superadmin; 400 revisi tanpa catatan; 409 bukan tahap `tinjau` |

Antrean pembimbing: `?pembimbing_id=<id saya>&status=diajukan` lalu pilih `tahap === 'tinjau'`. Parameter paginasi sama dengan rute daftar lain (lihat `dosen-service.ts`).

## Kaprodi

| Method | Rute | Isi | Hasil |
|---|---|---|---|
| GET | `/pembimbing-ta?prodi_id=` | — | `{ data: { mahasiswa: Orang, pembimbing: Orang \| null, judul: { status, tahap, judul, tema } \| null }[], total }` |
| GET | `/pembimbing-ta/dosen?prodi_id=` | — | `{ data: { id, nama_lengkap }[] }` |
| PUT | `/pembimbing-ta` | `{ mahasiswa_id, dosen_id }` | `{ pembimbing: Orang }`; pengajuan berjalan ikut pindah; 400 dosen tidak memenuhi syarat; 502 bila AlurKerja gagal |
| GET | `/judul/statistik-tema?prodi_id=` | `prodi_id` opsional | lihat [05](05-visualisasi-tema.md) |

Daftar prodi kaprodi: `user.units` (`peran === 'kaprodi' && tipe === 'prodi'`), seperti `components/dosen/halaman-prodi.tsx`.
