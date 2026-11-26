Nama: Muhammad Daffa Raihan  
NIM: 25917045

# UI Refinement Admin dan Dosen

Dokumen ini menjadi acuan penyegaran tampilan untuk area Admin dan Dosen pada Student Gateway. Halaman mahasiswa, termasuk `/beranda`, tidak termasuk dalam scope refinement ini.

## Tujuan

- Membuat area Admin dan Dosen terlihat lebih modern, rapi, dan konsisten.
- Memperjelas hierarchy antara navigasi, judul halaman, data utama, dan aksi pengguna.
- Mengurangi tampilan yang terlalu padat tanpa menghilangkan informasi penting.
- Menjaga pola interaksi yang konsisten antara dashboard, tabel, form, modal, dan status feedback.

## Scope

Refinement diterapkan pada:

- `/admin`
- `/admin/beranda`
- `/admin/struktur`
- `/admin/orang`
- `/admin/penugasan`
- `/admin/dpa`
- `/admin/audit`
- `/admin/panduan`
- `/dosen`
- `/dosen/bimbingan`
- `/dosen/riwayat`
- `/dosen/tinjau`
- `/dosen/prodi`
- Detail pengajuan dosen

Tidak termasuk:

- `/beranda` mahasiswa
- `/login`
- Alur assessment mahasiswa
- Perubahan business logic, API, role permission, atau struktur database

## Arah visual

### 1. Layout

- Pertahankan sidebar sebagai navigasi utama Admin dan Dosen.
- Gunakan lebar konten yang konsisten dan batasi area baca agar tabel atau kartu tidak terlalu melebar.
- Berikan jarak yang lebih jelas antara breadcrumb, judul halaman, filter, dan konten.
- Pada layar kecil, sidebar berubah menjadi drawer dengan overlay yang mudah ditutup.
- Header tetap ringkas dan memprioritaskan judul halaman, status pengguna, serta aksi akun.

### 2. Typography

- Gunakan satu font UI modern secara konsisten, disarankan Inter atau Plus Jakarta Sans.
- Judul halaman menggunakan bobot 600–700.
- Body text menggunakan ukuran 13–14px dengan line-height sekitar 1.5–1.6.
- Metadata, label, dan helper text dibuat lebih kecil serta memakai warna muted.
- Hindari penggunaan terlalu banyak ukuran font dalam satu halaman.

### 3. Warna

- Gunakan biru brand sebagai warna aksi utama dan active state.
- Gunakan surface netral untuk background halaman, misalnya `#f7f9fc`.
- Gunakan putih untuk card dan panel data.
- Gunakan warna status secara konsisten:
  - Success: hijau
  - Warning: amber
  - Error: merah
  - Informasi: biru
- Pastikan teks utama memenuhi kontras yang cukup terhadap background.

### 4. Card dan panel

- Gunakan radius 12–16px secara konsisten.
- Gunakan border tipis atau shadow ringan, bukan keduanya secara berlebihan.
- Kartu statistik menampilkan angka utama, label singkat, icon, dan perubahan atau konteks data.
- Kartu konten memiliki padding yang konsisten, disarankan 20–24px.
- Hover hanya digunakan pada elemen yang dapat diklik.

### 5. Tabel

- Header tabel diberi background netral yang sangat ringan.
- Gunakan row height yang cukup untuk scanning, tetapi jangan terlalu tinggi.
- Kolom aksi ditempatkan konsisten di sisi kanan.
- Status memakai `Tag` dengan warna yang mudah dibedakan.
- Tabel panjang wajib memiliki pagination atau horizontal scroll yang jelas.
- Empty state harus menjelaskan kondisi dan, bila relevan, menyediakan aksi berikutnya.

### 6. Form, modal, dan feedback

- Input memiliki tinggi dan radius yang seragam.
- Label form selalu terlihat; placeholder bukan pengganti label.
- Validasi ditampilkan dekat dengan field yang bermasalah.
- Modal memiliki judul, isi, dan footer action yang jelas.
- Aksi destruktif menggunakan warna danger dan memerlukan konfirmasi.
- Loading, success, error, dan unauthorized state harus memiliki feedback yang jelas.

## Penyesuaian Ant Design

Area Admin dan Dosen sudah menggunakan `ConfigProvider` Ant Design melalui `components/admin/antd-provider.tsx`. Theme token perlu dijadikan sumber utama styling komponen Ant Design.

Contoh arah token:

```tsx
<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#2858e8',
      colorBgLayout: '#f7f9fc',
      colorText: '#172744',
      colorTextSecondary: '#667594',
      borderRadius: 12,
      fontFamily: "'Inter', sans-serif",
    },
    components: {
      Card: { borderRadiusLG: 16 },
      Button: { controlHeight: 38, borderRadius: 9 },
      Input: { controlHeight: 40, borderRadius: 9 },
      Select: { controlHeight: 40, borderRadius: 9 },
      Table: { headerBg: '#f7f9fc' },
    },
  }}
>
```

Override CSS `.ant-*` hanya digunakan untuk kebutuhan layout atau kasus yang tidak tersedia melalui token. Hindari `!important` kecuali ada konflik style yang sudah diverifikasi.

## Prioritas implementasi

### Prioritas tinggi

1. Rapikan `AdminShell` dan `DosenShell` agar struktur sidebar, header, breadcrumb, dan content memiliki pola yang sama.
2. Samakan token Ant Design dan variable CSS untuk warna, typography, radius, spacing, dan shadow.
3. Perbarui dashboard Admin dan Dosen: statistik, chart, card, dan empty state.
4. Perbaiki tabel pengajuan, bimbingan, riwayat, orang, dan audit.
5. Pastikan state loading, error, unauthorized, dan empty konsisten.

### Prioritas menengah

1. Tambahkan hover dan focus state yang konsisten.
2. Rapikan modal dan form CRUD.
3. Perbaiki responsive behavior pada tablet dan mobile.
4. Tambahkan confirmation pattern untuk aksi berisiko.

### Prioritas rendah

1. Fine-tuning icon, ilustrasi, dan micro-interaction.
2. Menambahkan shortcut atau quick action jika terbukti membantu workflow.
3. Menyempurnakan animasi transisi dengan durasi singkat.

## Kriteria selesai

- Tampilan Admin dan Dosen menggunakan token visual yang konsisten.
- Tidak ada halaman Admin atau Dosen yang memiliki spacing, radius, atau button style yang berbeda tanpa alasan UX.
- Tabel dapat digunakan dengan baik pada desktop dan mobile.
- Semua status utama memiliki feedback visual dan teks yang jelas.
- Kontras teks dan focus state dapat digunakan oleh keyboard.
- Tidak ada perubahan pada scope mahasiswa atau business logic.
- Satu Dosen PA dapat memiliki penugasan aktif di beberapa Prodi; detail Prodi tetap menjadi konteks langsung untuk menambah atau mengakhiri penugasan pada Prodi tersebut.
- Admin dapat membuat akun dosen langsung dari detail Prodi; proses membuat data orang, akun login, dan penugasan Dosen PA sekaligus. Sandi wajib diisi admin dan tidak dibuat otomatis.
- Build dan lint berhasil setelah perubahan.

## File utama yang menjadi acuan

- `components/admin/antd-provider.tsx`
- `components/admin/admin-shell.tsx`
- `components/dosen/dosen-shell.tsx`
- `app/admin/admin.css`
- `components/admin/admin-dashboard.tsx`
- `components/dosen/tabel-pengajuan.tsx`
- `components/dosen/halaman-bimbingan.tsx`
- `components/dosen/halaman-riwayat.tsx`
- `components/dosen/halaman-tinjau.tsx`

