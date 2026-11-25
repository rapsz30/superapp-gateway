# 02. Keputusan desain

## Sudah diputuskan pengguna

| # | Keputusan |
|---|---|
| D1 | Tata letak **sidebar** (menu di kiri), bukan tab horizontal |
| D2 | Komponen UI memakai **Ant Design** (`antd`) |
| D3 | Alamat utama admin: **`/admin/beranda`** (`/admin` sudah mengalihkan ke sana) |

## Keputusan yang diambil di dokumen ini (bisa diubah bila pengguna keberatan)

| # | Keputusan | Alasan |
|---|---|---|
| D4 | Satu menu = satu rute (`/admin/struktur`, `/admin/orang`, ...) | URL bisa disalin dan dibuka langsung; tombol kembali browser bekerja; kode terpecah per halaman |
| D5 | `/admin/beranda` jadi **halaman ringkasan** (kartu angka + jalan pintas), bukan salinan Struktur | "Beranda" di sidebar harus punya isi. Angka diambil dari `total` pada daftar API yang sudah ada (tanpa endpoint baru) |
| D6 | Layout admin (`app/admin/layout.tsx`) membungkus **semua** rute admin dengan provider Ant Design + pemeriksa peran + shell sidebar | Satu tempat untuk penjaga akses dan navigasi |
| D7 | Ant Design **hanya dimuat di bawah `/admin`**, bukan di layout akar | Halaman mahasiswa (`/beranda`, `/login`) tidak boleh membayar ukuran bundel antd dan gayanya tidak boleh bocor |
| D8 | Bahasa Ant Design diatur `id_ID` | Teks bawaan (paginasi, kosong, tanggal) berbahasa Indonesia |
| D9 | Tema: warna utama `#2858e8` (sama dengan `--blue`), font Roboto yang sudah dimuat | Tampilan tetap seragam dengan halaman mahasiswa |
| D10 | Tidak ada mode gelap pada tahap ini | Halaman lain tidak punya |
| D11 | Tidak ada perubahan backend | Redesain tampilan saja |

## Menu sidebar

| Menu | Rute | Ikon (`@ant-design/icons`) | Terlihat oleh |
|---|---|---|---|
| Beranda | `/admin/beranda` | `DashboardOutlined` | semua pengelola |
| Struktur | `/admin/struktur` | `ApartmentOutlined` | semua pengelola (hanya superadmin yang bisa mengubah) |
| Orang & akun | `/admin/orang` | `TeamOutlined` | semua pengelola |
| Penugasan | `/admin/penugasan` | `SolutionOutlined` | semua pengelola |
| DPA (bimbingan) | `/admin/dpa` | `UserSwitchOutlined` | semua pengelola |
| Panduan akademik | `/admin/panduan` | `FileTextOutlined` | semua pengelola |
| Jejak audit | `/admin/audit` | `AuditOutlined` | **hanya superadmin** |

Di bagian bawah sidebar: tautan "Kembali ke beranda" (`/beranda`) dan tombol "Keluar" (`authService.logout()` lalu `router.push('/login')`). Sidebar bisa diciutkan (`collapsible`); di layar sempit (`breakpoint="lg"`, `collapsedWidth=0`) otomatis tersembunyi dengan pemicu di header.

"Pengelola" = peran `superadmin`, `dekan`, `kajur`, atau `kaprodi`. Selain itu: halaman "Tidak ada akses" (`Result` status 403 dengan tombol ke `/beranda`).

## Header

Satu baris tipis: judul halaman aktif di kiri; di kanan nama pengguna + peran (`Tag`), menu akun (`Dropdown`: Keluar).

## Breadcrumb dan judul

Gunakan `PageHeader`-setara: `Breadcrumb` (Admin › nama menu) + `Typography.Title level={3}`. Catatan: komponen `PageHeader` dihapus dari antd v5; rakit sendiri dari `Breadcrumb` + `Flex`.

## Terbuka (tanyakan pengguna bila relevan, jangan menebak diam-diam)

1. **Bahasa**: seluruh teks admin Indonesia. Apakah perlu mengikuti `LanguageProvider` (id/en) yang dipakai halaman mahasiswa? Asumsi dokumen ini: **tidak**, admin hanya Indonesia.
2. **Versi antd**: pilih versi stabil terbaru yang mendukung React 19. Lihat [03](03-pemasangan-antd.md) untuk apa yang harus diperiksa. Jangan menebak nomor versi; baca hasil `pnpm view antd version` dan catatan rilisnya.
3. **Dashboard**: kartu mana saja yang berguna untuk pengguna (asumsi: jumlah fakultas/jurusan/prodi aktif, orang, bimbingan aktif, pengajuan KHS berjalan)? Daftar di [06](06-beranda-dan-struktur.md) hanyalah usulan.
4. **Unggah massal panduan/akun**: di luar cakupan.
