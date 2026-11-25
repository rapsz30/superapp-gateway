# 05. Komponen bersama dan pemetaan ke Ant Design

## Dipertahankan (pindahkan ke `components/admin/data.tsx`, isi logika sama)

Sumber sekarang: `components/admin/ui.tsx`.

| Nama | Fungsi | Catatan |
|---|---|---|
| `StrukturProvider({ isSuper, children })` | Memuat `GET /struktur?semua=true`; menyediakan `pohon`, `unit: Map<id, UnitInfo>`, `prodi: UnitInfo[]`, `isSuper`, `muat()` | Ganti `Notice` galat dengan `Alert type="error"` bila pemuatan gagal |
| `useStruktur()` | Konteks di atas | Lempar galat bila di luar provider |
| `UnitInfo` | `{ id, nama, kode, tipe, jalur, aktif }`; `jalur` = "Jurusan › Prodi" atau "Fakultas › Jurusan" | Dipakai untuk label dropdown |
| `namaUnit(unit, id)` | nama unit dari id, `'—'` bila kosong | |
| `useLoad(fn, deps)` | `{ data, loading, error, reload }`. Penjaga urutan (`urut`) mencegah respons lama menimpa yang baru | Pertahankan persis; ini mencegah balapan saat filter berubah cepat |
| `useOrang(ids)` | fungsi `id → nama` dengan cache modul `cacheOrang` | Ambil per-id `GET /orang/{id}`; gagal → tampil 8 karakter id + `…` |
| `lupakanOrang(id)` | buang satu id dari cache | Panggil setelah `PATCH /orang/{id}` atau perubahan akun |
| `useAksi()` | `{ sibuk, galat, ok, jalankan(fn, pesanOk) }` | **Ganti** dengan `App.useApp().message` (lihat tabel di bawah); boleh dipertahankan bila perlu status `sibuk` per tombol |
| `tanggal(s)`, `waktu(s)` | format `YYYY-MM-DD` dan `toLocaleString('id-ID')` | Bisa diganti `dayjs` |

`useLoad` tidak tahu antd; ia cocok dipasangkan dengan `Table loading={loading}`.

## Pemetaan komponen lama → Ant Design

| Lama (`ui.tsx` / CSS `.adm-*`) | Ant Design | Catatan |
|---|---|---|
| `Notice tone="error"` | `Alert type="error" showIcon closable` untuk galat yang harus tetap terlihat; `message.error()` untuk galat aksi sesaat | Galat pemuatan data = `Alert` di atas tabel; galat aksi = `message` |
| `Notice tone="ok"` | `message.success()` | |
| `Notice` info | `Alert type="info" showIcon` | |
| `Kartu` | `Card` (`title`, `extra`) | |
| `Field` | `Form.Item` (`label`, `extra`, `rules`) | Gunakan `Form` dengan `layout="vertical"` |
| `Badge` | `Tag` (`color`: `green` aktif, `gold` draf/ditangguhkan, `red` nonaktif, `default` arsip, `blue` peran) | Pakai `Badge status` hanya untuk titik status kecil |
| tabel `.adm-table` | `Table` (`rowKey`, `columns`, `loading`, `pagination`, `scroll={{ x: 'max-content' }}`) | Paginasi sisi server, lihat di bawah |
| `Pager` | `Table.pagination={{ current, pageSize, total, onChange, showSizeChanger:false, showTotal }}` | Server memakai `halaman` mulai 1 dan `ukuran` |
| `Kosong` | `Table locale.emptyText` atau `Empty` | |
| `window.confirm` | `Popconfirm` (tombol baris) atau `Modal.confirm` (tindakan besar) | Teks konfirmasi sama persis dengan yang sekarang (isi bermakna: lihat halaman masing-masing) |
| `SandiSementara` | `Modal` (`closable={false}`, `maskClosable={false}`, `keyboard={false}`) berisi `Typography.Text code copyable` + tombol "Sudah saya catat" | Satu-satunya cara menutup: tombol itu |
| `OrangPicker` | `Select showSearch filterOption={false}` dengan `onSearch` yang debounce 250 ms memanggil `GET /orang?q=&peran=&prodi_id=&ukuran=8`; `labelInRender` / `optionRender` menampilkan nama + NIM/NIDN + peran | Nilai = objek `Orang` (simpan di state), bukan hanya id, karena halaman butuh nama |
| `SelectProdi` | `Select showSearch optionFilterProp="label"` dengan opsi dari `useStruktur().prodi` | Label = `jalur` UnitInfo; tampilkan "(nonaktif)" bila `aktifSaja=false` |
| tab horizontal | menu sidebar + rute | |
| `.adm-tree` | `Tree` (`treeData`, `titleRender`) atau `Table` bersarang (`expandable`) | Lihat [06](06-beranda-dan-struktur.md) |
| input tanggal native | `DatePicker` (nilai ke string `YYYY-MM-DD` saat dikirim) | Server menerima `date` ISO |
| `<input type="file">` | `Upload` dengan `beforeUpload={() => false}` (pegang `File` sendiri, kirim lewat `FormData` di service) atau `Upload.Dragger` | Jangan biarkan antd mengunggah sendiri; unggah lewat `adminService` agar token dan refresh bekerja |

## Pola form

- `Form` dengan `layout="vertical"`, `onFinish` yang memanggil `adminService.*`.
- Tombol kirim: `Button type="primary" htmlType="submit" loading={sibuk}`.
- `rules` hanya untuk bantuan pengguna (wajib, panjang). **Server tetap sumber kebenaran**; tampilkan pesan galat server (`errorMessage(e)`) bila ditolak, mis. kode duplikat atau aturan unik.
- Pola kotak buat/ubah: `Drawer` (lebar 480) atau `Modal` untuk form singkat. Disarankan **`Modal` untuk form ≤ 5 bidang**, **`Drawer` untuk detail orang** (yang berisi beberapa bagian).

## Paginasi sisi server (pola seragam)

```
state: halaman (1), filter...
useLoad(() => adminService.daftarX({ ...filter, halaman, ukuran: 20 }), [filter..., halaman])
Table dataSource={data?.data} pagination={{ current: halaman, pageSize: 20, total: data?.total, onChange: setHalaman }}
Setiap filter berubah -> setHalaman(1)
```

## Pesan galat

Pesan server sudah berbahasa Indonesia dan ramah pengguna ("Prodi masih memiliki 3 mahasiswa aktif."). Tampilkan apa adanya lewat `message.error(errorMessage(e))`. Jangan menerjemahkan atau meringkasnya. Untuk galat yang butuh dibaca lama (mis. 409 aturan bisnis) gunakan `Alert` di dalam modal/drawer, bukan `message` yang hilang dalam 3 detik.
