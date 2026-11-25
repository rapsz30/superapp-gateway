# 12. Pengujian dan verifikasi

## Menjalankan aplikasi untuk uji

### Opsi A: stack lengkap (disarankan bila Docker tersedia)

```powershell
# dari superapp-gateway/
docker compose up -d --build        # butuh services/microcred/.env dan services/judul/.env
cd frontend
pnpm dev                             # http://localhost:3000, gateway default http://127.0.0.1:8080
```

- Port host debug sudah dipindah di `docker-compose.override.yml`: microcred 18000, judul 18001, identity 18002, matkul 13000, verifier 18100, PocketBase 8090, gateway 8080. (8000–8002 di Windows termasuk rentang yang dicadangkan; 8100 dipakai AlurKerja lokal; 3000 dipakai `next dev`.) Cek `netstat -ano | findstr :8080` bila gateway tidak bisa naik.
- Bila ada aplikasi lain di 8080, ubah `GATEWAY_PORT` lewat berkas `.env` di root (`GATEWAY_PORT=8088`) dan set `API_BASE_URL=http://127.0.0.1:8088` untuk frontend.
- Buat superadmin pertama (sekali):
  ```powershell
  docker compose run --rm identity-api python -m src.cli buat-superadmin --email <email> --nama "<nama>"
  ```
  Sandi sementara dicetak sekali; login pertama memaksa ganti sandi. **Jangan menulis sandi ke dokumen atau kode.**

### Opsi B: identity lokal tanpa Docker penuh (cara yang dipakai saat membuat halaman lama)

1. Basis data Postgres sementara (mis. kontainer uji di port acak), venv Python di `services/identity/.venv`.
2. Env: `DATABASE_URL`, `JWT_SECRET`, `INTERNAL_TOKEN`, `MATKUL_SERVICE_TOKEN`, `PANDUAN_DIR` (folder sementara), `BCRYPT_ROUNDS=4` (cepat). `alembic upgrade head`, lalu `python -m src.cli buat-superadmin ... --sandi <sandi>`. Ganti sandi sementara lewat `POST /auth/ganti-sandi` agar login UI langsung masuk.
3. `uvicorn src.api.main:app --port 18002`.
4. Proksi kecil yang meneruskan `/api/identity/*` ke identity (tanpa awalan) dan sisanya ke Next (ini yang menggantikan NGINX). Frontend dijalankan **build produksi** (lihat jebakan di bawah).

## Jebakan pengujian (sudah pernah kena)

| Jebakan | Gejala | Solusi |
|---|---|---|
| `next dev` lewat proksi/origin lain | halaman tidak hidrasi, tombol tidak bereaksi, konsol penuh WebSocket `_next/hmr` 403 | gunakan `npx next build` lalu `npx next start -p <port>` untuk uji lewat proksi; atau buka `localhost:3000` langsung |
| Login tersubmit sebagai GET dengan sandi di URL | URL jadi `/login?email=...&password=...` | tunggu hidrasi (beberapa detik setelah halaman terbuka) sebelum mengetik; pada otomasi gunakan `form_input` lalu Enter |
| `window.confirm`/dialog bawaan memblokir otomasi | langkah macet | setelah redesain dialognya `Popconfirm`/`Modal.confirm` (elemen DOM biasa, bisa diklik). Selama masa transisi: `window.confirm = () => true` lewat konsol |
| Pilihan `<select>` native sulit diisi otomasi | — | `Select` antd bukan `<select>`; klik untuk membuka lalu klik opsi, atau gunakan `find`/`read_page` untuk mendapat ref opsi |
| `next dev` membuat `frontend/AGENTS.md` | berkas tak dikenal di `git status` | hapus |
| Build tidak mengecek tipe | `ignoreBuildErrors: true` | jalankan `npx tsc --noEmit` terpisah |
| Port 8080 sudah dipakai | gateway tidak naik / login dijawab aplikasi lain | lihat Opsi A |
| Sandi sementara tidak terlihat lagi | disengaja | catat saat muncul; atur ulang bila hilang |

## Pemeriksaan otomatis (wajib hijau)

```powershell
cd frontend
npx tsc --noEmit        # tidak boleh ada keluaran
npx next build          # semua rute /admin/* terdaftar
npm test                # 7 tes (tests/api.test.mjs)
```

Tidak ada tes komponen React di proyek ini. Penulis tidak diwajibkan menambahkannya; bila menambah, jangan memasang kerangka uji besar tanpa alasan kuat (pilih yang ringan dan cocok Next 16/React 19, dan perbarui CI `.github/workflows/ci.yml` bila menambah skrip).

## Daftar uji manual di browser (jalankan semuanya setelah selesai)

Persiapan: login sebagai superadmin; `viewport` desktop, lalu ponsel (375 px).

1. `/admin` mengalihkan ke `/admin/beranda`. Sidebar tampil; menu sesuai peran (Audit hanya superadmin).
2. Beranda menampilkan kartu angka tanpa galat; kartu yang gagal tidak merobohkan halaman.
3. Struktur: tambah fakultas → jurusan → prodi (dengan batas SKS 20). Ubah nama prodi → batas SKS **tetap 20**. Nonaktifkan prodi tanpa mahasiswa. Nonaktifkan fakultas yang masih punya jurusan aktif → pesan galat server tampil.
4. Panduan: pilih prodi → unggah PDF (`Panduan-Akademik-Informatika-20212022.docx-compressed.pdf` di folder `project-baru/`) → muncul draf → Aktifkan → status aktif. "Buka PDF" membuka berkas. Unggah file non-PDF → ditolak.
5. Orang: tambah dosen (NIDN) + akun (sandi kosong → modal sandi sementara tidak bisa tertutup tak sengaja; tombol salin bekerja). Tambah mahasiswa (NIM) + akun + daftarkan ke prodi. Coba impor CSV kecil (dua baris valid, satu gagal).
6. Penugasan: jadikan dosen `dosen_pa` pada prodi; pilihan unit mengikuti peran. Coba buat kaprodi kedua pada prodi yang sama → 409 tampil.
7. DPA: buat bimbingan mahasiswa → dosen. Alihkan massal ke dosen lain. Akhiri.
8. Audit: tindakan di atas muncul; baris dapat diperluas; filter aksi `panduan.aktifkan` bekerja.
9. Keluar (`Keluar` di sidebar/menu akun) → `/login`; membuka `/admin/beranda` lagi tanpa sesi → dialihkan ke `/login`.
10. Login sebagai mahasiswa (tanpa peran pengelola) lalu buka `/admin/beranda` → halaman 403 dalam shell, tautan kembali ke `/beranda`.
11. Ponsel 375 px: sidebar menjadi laci (pemicu di header), tabel dapat digeser horizontal, tidak ada gulir horizontal pada halaman, modal/drawer tidak keluar layar.
12. `/login` dan `/beranda` (halaman mahasiswa) tampil sama seperti sebelum perubahan.

## Pembersihan setelah menguji

- Hentikan server uji, hapus basis data sementara, hapus `frontend/AGENTS.md` bila muncul.
- Jangan meninggalkan akun/token uji di berkas yang dilacak git.
