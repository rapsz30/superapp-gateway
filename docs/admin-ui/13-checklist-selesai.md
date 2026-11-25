# 13. Checklist selesai dan larangan

## Urutan kerja yang disarankan

1. Baca [README](README.md), [01](01-keadaan-sekarang.md), [02](02-keputusan-desain.md). Jalankan aplikasi sekarang dan lihat halaman lama berfungsi ([12](12-pengujian.md)).
2. [03](03-pemasangan-antd.md): pasang antd, buat provider, pastikan `/login` dan `/beranda` tidak berubah.
3. [04](04-struktur-berkas-dan-rute.md) + [05](05-komponen-bersama.md): shell sidebar, rute kosong per menu, pindahkan hook data ke `data.tsx`, komponen bersama.
4. Halaman satu per satu, uji tiap halaman sebelum lanjut: Struktur ([06](06-beranda-dan-struktur.md)) → Orang ([07](07-orang-dan-akun.md)) → Panduan ([09](09-panduan-dan-audit.md)) → Penugasan, DPA ([08](08-penugasan-dan-dpa.md)) → Audit → Beranda (ringkasan, terakhir karena paling tidak kritis).
5. Hapus berkas lama (`admin.css`, `admin-app.tsx`, `ui.tsx`, `tab-*.tsx`) **setelah** semua halaman baru lulus.
6. Jalankan seluruh daftar uji manual di [12](12-pengujian.md) dan pemeriksaan otomatis.
7. Perbarui dokumen yang menyebut halaman lama (lihat bawah).

## Kriteria selesai (semua harus ya)

- [ ] `/admin/beranda` dan semua rute di [04](04-struktur-berkas-dan-rute.md) ada, memakai tata letak sidebar Ant Design.
- [ ] Tidak ada lagi tab horizontal, `admin.css`, atau kelas `.adm-*`.
- [ ] Semua tampilan memakai komponen Ant Design (tabel, form, modal/drawer, notifikasi, tag, konfirmasi). Tidak ada `window.confirm`/`alert`.
- [ ] Setiap fitur dari halaman lama masih ada dan bekerja: struktur CRUD, orang + akun + keanggotaan + impor CSV, penugasan, bimbingan + alihkan massal, panduan (unggah/aktifkan/buka PDF), audit.
- [ ] Sandi sementara ditampilkan sekali dengan cara yang aman dari tertutup tak sengaja, ada tombol salin.
- [ ] Mengubah prodi tidak mengosongkan batas SKS (uji nyata).
- [ ] Hak akses sesuai [11](11-hak-akses.md): tombol hanya-superadmin disembunyikan dari peran lain; `/admin/audit` 403 untuk non-superadmin; non-pengelola 403 di seluruh `/admin/*`.
- [ ] Ant Design **tidak** dimuat di `/login` dan `/beranda`; tampilannya tidak berubah.
- [ ] Layar 375 px: sidebar menjadi laci, tabel dapat digeser, tanpa gulir horizontal halaman.
- [ ] `npx tsc --noEmit` bersih, `npx next build` lulus, `npm test` 7/7 lulus.
- [ ] Daftar uji manual di [12](12-pengujian.md) dijalankan; hasil dilaporkan jujur (apa yang diuji, apa yang tidak).
- [ ] Tidak ada rahasia di kode/dokumen; `frontend/AGENTS.md` tidak ada; tidak ada berkas sementara.

## Dokumen yang perlu diperbarui saat selesai

- `docs/identity/README.md`, bagian "Halaman administrasi": alamat (`/admin/beranda`, rute per menu), tabel menu, dan kode sumber (`frontend/app/admin`, `frontend/components/admin`).
- `docs/admin-ui/01-keadaan-sekarang.md`: tandai sebagai riwayat atau perbarui ke keadaan baru (atau hapus bagian "akan diganti").
- Bila ada catatan frontend di `docs/port-map.md` terkait `/admin`, sesuaikan.

## Larangan

- Jangan commit atau push tanpa diminta pengguna. Jangan membuat cabang baru.
- Jangan mengubah `services/identity` (backend), `src/lib/api.ts`, `docker-compose*.yml`, `gateway/`, atau halaman mahasiswa (`app/beranda`, `app/login`, komponen mahasiswa) selain yang disebut dokumen ini. Satu-satunya perubahan sah di luar `admin`: dependensi di `package.json` + berkas kunci.
- Jangan memasang pustaka UI lain di samping Ant Design (satu sistem desain saja). Ikon dari `@ant-design/icons` (boleh tetap memakai `lucide-react` hanya di kode lama non-admin).
- Jangan memanggil API dengan `fetch` langsung; selalu `adminService`/`apiFetch`.
- Jangan menyimpan token, sandi, atau laporan impor di `localStorage`/`sessionStorage` selain yang sudah dilakukan `tokenStore`.
- Jangan menyembunyikan galat server; tampilkan kalimat aslinya.
- Jangan mengklaim selesai tanpa menjalankan [12](12-pengujian.md). Bila sesuatu tidak sempat diuji, tulis begitu.

## Pertanyaan yang boleh diajukan ke pengguna

Hanya bila benar-benar menghalangi: (1) isi kartu Beranda, (2) apakah teks admin perlu dwibahasa, (3) versi antd bila ada batasan. Selain itu, ambil keputusan masuk akal, catat di [02](02-keputusan-desain.md), dan lanjut.
