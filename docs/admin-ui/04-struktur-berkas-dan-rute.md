# 04. Struktur berkas dan peta rute

## Pohon berkas target

```
frontend/
  app/admin/
    layout.tsx                 server: metadata (noindex) + <AdminShell> pembungkus klien
    page.tsx                   redirect('/admin/beranda')   (SUDAH ADA, pertahankan)
    beranda/page.tsx           <BerandaAdmin />
    struktur/page.tsx          <HalamanStruktur />
    orang/page.tsx             <HalamanOrang />
    penugasan/page.tsx         <HalamanPenugasan />
    dpa/page.tsx               <HalamanDpa />
    panduan/page.tsx           <HalamanPanduan />
    audit/page.tsx             <HalamanAudit />      (khusus superadmin)
  components/admin/
    antd-provider.tsx          ConfigProvider + AntdRegistry + App   (lihat 03)
    admin-shell.tsx            Layout + Sider + Header + penjaga peran + StrukturProvider
    data.tsx                   hook & provider data (dari ui.tsx lama, tanpa komponen visual)
    komponen/
      pilih-orang.tsx          Select pencarian orang (pengganti OrangPicker)
      pilih-unit.tsx           Select prodi / unit
      sandi-sementara.tsx      Modal sandi sementara
      judul-halaman.tsx        Breadcrumb + judul + aksi
    halaman/
      beranda.tsx  struktur.tsx  orang.tsx  penugasan.tsx  dpa.tsx  panduan.tsx  audit.tsx
  src/services/admin-service.ts   TIDAK DIUBAH
```

Berkas lama yang **dihapus** setelah semuanya pindah: `app/admin/admin.css`, `components/admin/{admin-app,ui,tab-*}.tsx`. Hapus hanya setelah halaman baru terbukti berfungsi (jangan meninggalkan impor yatim; `tsc` akan menangkapnya).

Penamaan boleh disesuaikan, asal konsisten dan satu halaman = satu berkas.

## Peta rute

| Rute | Komponen | Akses |
|---|---|---|
| `/admin` | redirect ke `/admin/beranda` | — |
| `/admin/beranda` | ringkasan | pengelola |
| `/admin/struktur` | pohon dan CRUD fakultas/jurusan/prodi | pengelola (ubah: superadmin) |
| `/admin/orang` | daftar orang + detail + akun + keanggotaan + impor | pengelola |
| `/admin/penugasan` | penugasan jabatan | pengelola |
| `/admin/dpa` | bimbingan DPA | pengelola |
| `/admin/panduan` | panduan akademik per prodi | pengelola |
| `/admin/audit` | jejak audit | superadmin |

Rute yang tidak boleh dimasuki peran (mis. `/admin/audit` oleh kaprodi): tampilkan `Result` 403 di dalam shell, **jangan** redirect diam-diam. Tautan menu audit juga disembunyikan.

## Shell (`admin-shell.tsx`)

Tanggung jawab, berurutan:
1. `useCurrentUser()`; selama `loading` tampilkan `Spin` layar penuh.
2. Bila `user` null (profil gagal dimuat): `Result` status `error` dengan tautan ke `/login`.
3. Hitung `isSuper` dan `pengelola` ([11](11-hak-akses.md)). Bila bukan pengelola: `Result` 403 + tombol ke `/beranda`.
4. Bungkus anak dengan `StrukturProvider` (dari `data.tsx`) supaya semua halaman berbagi pohon struktur.
5. Render `Layout`:
   - `Sider` (`collapsible`, `breakpoint="lg"`, `collapsedWidth` 0 di layar sempit saat `broken`) berisi logo teks "Student Gateway · Admin" dan `Menu mode="inline"`.
   - `selectedKeys` diturunkan dari `usePathname()` (cocokkan awalan rute).
   - Item menu memakai `next/link` (`<Link href=...>`), bukan `router.push` di `onClick`, agar klik-tengah dan "buka di tab baru" bekerja.
   - `Header` dengan pemicu sidebar (layar sempit), judul, dan menu akun.
   - `Content` dengan `padding: 24` (16 di ponsel) dan `children`.

Karena shell ada di `layout.tsx`, ia **tidak dipasang ulang** saat pindah rute; `StrukturProvider` hanya memuat sekali per sesi kunjungan admin. Pastikan `muat()` tetap dipanggil setelah mengubah struktur.

## Tautan masuk dari halaman mahasiswa

Sudah ada di `app/beranda/page.tsx` (`href="/admin/beranda"`). Tidak perlu diubah.

## Yang tidak boleh dilakukan

- Jangan menaruh provider antd di `app/layout.tsx` (D7).
- Jangan menambah rute di luar daftar di atas tanpa mengubah dokumen ini.
- Jangan mengubah `src/lib/api.ts` (logika refresh token sensitif; ada tes).
