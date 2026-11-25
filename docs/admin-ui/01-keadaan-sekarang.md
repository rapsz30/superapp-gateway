# 01. Keadaan sekarang

## Tumpukan frontend

- `frontend/`: Next.js **16.4.6** (App Router), React **19.2.9**, TypeScript 5.7, Tailwind **4** (`@tailwindcss/postcss`), `lucide-react`, `shadcn`/`@base-ui/react` (hanya `components/ui/button.tsx`).
- `package.json` menyebut `packageManager: pnpm@12.8.1`. **Cek berkas kunci yang ada** (`pnpm-lock.yaml` atau `package-lock.json`) sebelum memasang paket, dan pakai pengelola paket yang sama.
- `next.config.mjs`: `typescript.ignoreBuildErrors: true` (!). Build **tidak** mengecek tipe. Selalu jalankan `npx tsc --noEmit` sendiri. Juga ada `rewrites`: `/api/:path*` diteruskan ke `API_BASE_URL` (bawaan `http://127.0.0.1:8080`, gateway NGINX).
- Gaya global: `app/globals.css` (sebagian besar diminifikasi per baris, 50 KB). Memuat `@import 'tailwindcss'`, variabel `:root` (`--navy`, `--blue`, `--border`, ...), dan aturan global `button { cursor:pointer; border:0 }`, `button, input { font:inherit }`, `* { box-sizing:border-box }`. Perhatikan interaksinya dengan Ant Design di [03](03-pemasangan-antd.md).
- Layout akar `app/layout.tsx` (server component) membungkus semuanya dengan `LanguageProvider` dan membaca cookie bahasa.

## Halaman admin yang ada (akan diganti)

Semua dibuat dalam satu sesi sebelumnya dan **berfungsi**; sudah diuji di browser.

```
frontend/
  app/admin/
    layout.tsx            impor admin.css, metadata
    page.tsx              redirect('/admin/beranda')
    beranda/page.tsx      <AdminApp />
    admin.css             semua gaya (prefiks .adm-), dihapus setelah redesain
  components/admin/
    admin-app.tsx         pemeriksa peran + tab horizontal
    ui.tsx                provider struktur, hook data, komponen kecil
    tab-struktur.tsx
    tab-orang.tsx
    tab-penugasan.tsx
    tab-bimbingan.tsx
    tab-panduan.tsx
    tab-audit.tsx
  src/services/admin-service.ts   klien API bertipe (DIPERTAHANKAN)
  app/beranda/page.tsx    sidebar beranda mahasiswa punya tautan "Administrasi" -> /admin/beranda
```

Tautan masuk: di `app/beranda/page.tsx`, komponen `Sidebar` menerima prop `showAdmin` (true bila peran ada di `superadmin|dekan|kajur|kaprodi`) dan menampilkan `<a href="/admin/beranda">` dengan ikon `Settings`.

## Cara kerja inti (jangan hilang saat menulis ulang)

1. **Autentikasi**: token ada di `localStorage` lewat `tokenStore` (`src/lib/api.ts`). `apiFetch` menambahkan `Authorization`, memperbarui token diam-diam saat 401 (refresh token sekali pakai, satu proses per tab + Web Locks), dan mengalihkan ke `/login` bila sesi habis. **Semua panggilan harus lewat `apiFetch`**, jangan `fetch` langsung. `ApiError` membawa `status` dan pesan Indonesia dari server; pakai `errorMessage(e)`.
2. **Profil dan peran**: `useCurrentUser()` (`src/hooks/use-current-user.ts`) memuat `GET /api/identity/auth/saya`. `user.roles` berisi mis. `["superadmin"]`. Tanpa token ia mengalihkan ke `/login`.
3. **Struktur dibagi ke semua halaman**: `StrukturProvider` (di `ui.tsx`) memuat `GET /struktur?semua=true` sekali dan menyediakan peta `unit` (id → nama/jalur), daftar `prodi`, `isSuper`, dan `muat()` untuk memuat ulang setelah perubahan. Dipakai semua tab untuk memilih prodi/unit dan menampilkan nama unit dari id.
4. **Nama orang dari id**: daftar penugasan/bimbingan/audit hanya berisi id orang. Hook `useOrang(ids)` mengambil `GET /orang/{id}` satu per satu dengan cache tingkat modul (`cacheOrang`) dan mengembalikan fungsi `id → nama`. `lupakanOrang(id)` membuang cache setelah data orang diubah.
5. **Sandi sementara tampil sekali**: respons `POST /akun`, `POST /akun/{id}/atur-ulang-sandi`, dan laporan `POST /orang/impor` memuat `sandi_sementara` **hanya pada respons itu**. UI wajib menampilkannya dengan jelas di tempat yang tidak hilang sebelum dibaca (kotak khusus sekarang; di Ant Design pakai `Modal` yang tidak bisa ditutup dengan klik di luar) dan menjelaskan bahwa tidak bisa dilihat lagi.
6. **Konfirmasi tindakan merusak** memakai `window.confirm` sekarang. Ganti dengan `Popconfirm`/`Modal.confirm`.

## Bug dan jebakan yang sudah ditemukan (harus tetap dihindari)

| Masalah | Penjelasan | Penanganan |
|---|---|---|
| Mengubah prodi menghapus batas SKS | `GET /struktur` **tidak** memuat `maks_sks_semester`. `PATCH /prodi/{id}` memakai `model_fields_set`: mengirim `maks_sks_semester: null` **mengosongkan** nilainya | Sebelum membuka form ubah prodi, ambil `GET /prodi/{id}` dan isi nilai dari sana. Saat menyimpan, kirim `maks_sks_semester` hanya bila memang ingin mengubahnya. Tombol aktif/nonaktif hanya mengirim `{aktif}` |
| Form login terkirim sebagai GET | Bila diklik sebelum hidrasi React, form memuat ulang halaman dengan email dan sandi di URL | Hanya soal pengujian: tunggu halaman siap (lihat [12](12-pengujian.md)) |
| `next dev` lewat proksi menolak | Next 16 memblokir sumber dev dari origin lain (403), halaman tidak hidrasi | Uji dengan `next build` + `next start`, atau buka langsung di `localhost` |
| `next dev` membuat `frontend/AGENTS.md` | Efek samping otomatis, tidak diinginkan | Hapus sebelum selesai (`rm frontend/AGENTS.md`) |
| Tabel hancur di ponsel | Kolom berisi `code` terpecah per huruf | Beri `scroll={{ x: ... }}` pada `Table` Ant Design |

## Perilaku server yang memengaruhi UI

- Semua daftar mengembalikan `{ data: [...], total: n }` dan menerima `halaman` (mulai 1) dan `ukuran` (1–200, bawaan 50).
- Aturan unik yang ditegakkan database (UI cukup menampilkan pesan galat server): satu dekan/kajur/kaprodi aktif per unit; satu DPA aktif per mahasiswa; satu panduan aktif per prodi; satu keanggotaan prodi aktif per orang.
- Server yang menegakkan hak akses (lihat [11](11-hak-akses.md)). UI hanya menyembunyikan tombol; jangan menganggap itu pengamanan.
