# 03. Memasang Ant Design (Next 16, React 19, Tailwind 4)

> Saya (penulis dokumen ini) **tidak menjalankan** langkah di bawah. Semua pernyataan tentang kompatibilitas harus diverifikasi saat memasang. Bila kenyataan berbeda dari dokumen ini, ikuti kenyataan dan perbarui dokumen.

## Paket

```powershell
cd frontend
# gunakan pengelola paket yang sama dengan berkas kunci yang ada
pnpm add antd @ant-design/icons @ant-design/nextjs-registry
```

Periksa sebelum memasang:
1. `pnpm view antd version peerDependencies` — pastikan peer `react` mencakup 19. Bila antd versi 5.x: perlu `@ant-design/v5-patch-for-react-19` (impor sekali di entri klien). Bila versi 6.x atau lebih baru: dukungan React 19 bawaan, tidak perlu patch. Baca catatan rilis, jangan menebak.
2. `pnpm view @ant-design/nextjs-registry peerDependencies` — pastikan mendukung Next 16 dan React 19.
3. Setelah terpasang, `npx tsc --noEmit` dan `npx next build` harus tetap lulus.

Pustaka tanggal: antd menggunakan `dayjs`; ikut terpasang sebagai dependensi antd. Lokal Indonesia: `import 'dayjs/locale/id'` dan `import idID from 'antd/locale/id_ID'`.

## Provider (hanya untuk rute admin)

Buat `frontend/components/admin/antd-provider.tsx` (`'use client'`):

```tsx
'use client'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { App, ConfigProvider } from 'antd'
import idID from 'antd/locale/id_ID'
import 'dayjs/locale/id'

export function AntdProvider({ children }: { children: React.ReactNode }) {
  return (
    <AntdRegistry>
      <ConfigProvider
        locale={idID}
        theme={{ token: { colorPrimary: '#2858e8', borderRadius: 8, fontFamily: "'Roboto', sans-serif" } }}
      >
        <App>{children}</App>
      </ConfigProvider>
    </AntdRegistry>
  )
}
```

- `AntdRegistry` menyalin gaya CSS-in-JS ke HTML server supaya tidak ada kilatan tanpa gaya (FOUC) di App Router.
- Bungkus dengan `<App>` agar `App.useApp()` menyediakan `message`, `notification`, `modal` yang sadar tema. **Jangan** memakai `message.success()` statis di luar `App`.
- Dipasang di `app/admin/layout.tsx` (D7), bukan `app/layout.tsx`. Layout akar tetap server component.

## Berdampingan dengan `globals.css` dan Tailwind

Aturan global yang ada:
- `button { cursor:pointer; border:0 }` dan `button, input { font:inherit }` (selektor elemen, spesifisitas rendah): kelas Ant Design (`.ant-btn`, dst.) lebih spesifik, jadi seharusnya menang. **Periksa** tombol `Button` default, `Input`, dan `Select` tampil benar (tepi, tinggi, font).
- Tailwind 4 `preflight` berada di `@layer base`, gaya antd tidak berlayer, jadi antd menang. Kalau ternyata ada tabrakan (tepi hilang, tinggi salah), opsi: `StyleProvider layer` dari `@ant-design/cssinjs` bersama `@layer` urutan `theme, base, antd, components, utilities` seperti di dokumentasi antd tentang Tailwind. Jangan mengubah `globals.css` besar-besaran: file itu dipakai halaman mahasiswa.
- `html, body { min-height:100% }` dan `body` tanpa latar: antd `Layout` mengatur latarnya sendiri (`colorBgLayout`), cukup.
- `.app { display:flex; height:100dvh; overflow:hidden }` milik halaman mahasiswa: **jangan** memakai kelas `.app` atau kelas generik lain dari `globals.css` di komponen admin.

## Pemuatan font

`globals.css` sudah `@import` Roboto dari Google Fonts. Tidak perlu memuat ulang; cukup set `fontFamily` di token.

## Ukuran bundel

Impor komponen bernama (`import { Table, Button } from 'antd'`); antd mendukung tree-shaking. Jangan mengimpor `antd/dist/antd.css` (antd v5+ memakai CSS-in-JS, tidak butuh berkas CSS).

## Pengujian setelah pemasangan

1. `npx tsc --noEmit` bersih.
2. `npx next build` lulus; rute `/admin/*` terdaftar.
3. Buka `/login` dan `/beranda` (halaman mahasiswa): **tampilannya tidak boleh berubah** dan tidak boleh memuat antd (D7). Cek di tab Network/Sources bahwa tidak ada chunk antd di rute itu.
4. `npm test` (7 tes `tests/api.test.mjs`) tetap lulus.
