# 05. Visualisasi tema terbanyak per prodi

Ini inti permintaan pengguna: **terlihat tema apa yang paling banyak diambil di suatu prodi**.

## Data: `GET /api/identity/judul/statistik-tema`

Akses: kaprodi, kajur, dekan (sesuai cakupan), superadmin. `?prodi_id=` opsional. Tanpa identitas mahasiswa.

```json
{
  "data": [
    {
      "prodi": { "id": "…", "kode": "IF", "nama": "Informatika" },
      "total": 7,
      "tema": [
        { "tema": "Keamanan Siber", "disetujui": 3, "berjalan": 1, "total": 4 },
        { "tema": "Data Science & Analitik", "disetujui": 1, "berjalan": 2, "total": 3 }
      ]
    }
  ]
}
```

- `tema` sudah terurut: `total` terbanyak dulu.
- Pengajuan dibatalkan tidak dihitung. `berjalan` = menunggu pembimbing atau perbaikan.
- Prodi tanpa pengajuan tidak muncul; `data: []` berarti belum ada sama sekali.
- Tema yang jumlahnya nol tidak ikut. Bila ingin menampilkan semua, gabungkan dengan `GET /judul/tema`.

## Layar: "Tema judul" (`/dosen/tema-judul`, menu Kaprodi)

1. Pilih prodi (superadmin/dekan/kajur bisa punya banyak; tanpa pilihan, tampilkan per prodi).
2. Angka ringkas: total judul, disetujui, tema teratas.
3. **Grafik batang horizontal bertumpuk** per tema (`disetujui` + `berjalan`), urut terbanyak. Nama tema panjang, jadi sumbu kategori di kiri. Pakai recharts seperti `halaman-analitik.tsx`.
4. Tabel di bawah grafik: tema, disetujui, berjalan, total, persentase.
5. Keadaan kosong: "Belum ada pengajuan judul di prodi ini."
6. Segarkan dengan `useMuat` (mis. 60 detik).

Gunakan dua warna tetap untuk disetujui dan berjalan; jangan mewarnai tiap tema berbeda pada grafik bertumpuk.

## Alternatif lewat Analytics AlurKerja

Tab **Judul Tugas Akhir** di `/dosen/analitik` mencerminkan dashboard AlurKerja yang memuat tema terbanyak dan tema per prodi (lihat [13](../identity/13-proses-alurkerja-penuh.md)). Kartu yang ditambahkan di Studio ikut tampil tanpa kode. Datanya lintas prodi, sedangkan halaman di atas mengikuti cakupan pengguna.
