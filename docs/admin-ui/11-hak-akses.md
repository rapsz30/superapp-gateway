# 11. Hak akses

**Server menegakkan semuanya** (`services/identity`). UI hanya menyembunyikan tombol agar pengguna tidak mencoba hal yang pasti ditolak. Jangan pernah menganggap tombol tersembunyi sebagai pengamanan, dan jangan menyembunyikan pesan 403 dari server bila terjadi.

## Siapa yang boleh membuka `/admin/*`

"Pengelola" = punya salah satu peran: `superadmin`, `dekan`, `kajur`, `kaprodi` (dari `user.roles`). Selain itu: 403 di dalam shell. Dosen PA saja dan mahasiswa tidak boleh.

## Matriks per fitur

| Fitur | superadmin | kaprodi | dekan / kajur |
|---|---|---|---|
| Lihat struktur | ya | ya | ya |
| Ubah struktur (fakultas, jurusan, prodi) | **ya** | tidak | tidak |
| Lihat orang | semua | dalam cakupan | dalam cakupan |
| Buat/ubah orang, impor CSV | **ya** | tidak | tidak |
| Buat akun, atur ulang sandi, ubah status akun | **ya** | tidak | tidak |
| Daftarkan mahasiswa ke prodi, ubah status keanggotaan (cuti/aktif/lulus/keluar) | ya | **prodi yang ia pimpin** | tidak |
| Pindah prodi | **ya** | tidak | tidak |
| Lihat penugasan | semua | miliknya + cakupan | miliknya + cakupan |
| Buat/akhiri penugasan | semua peran | **hanya `dosen_pa` pada prodi yang ia pimpin** | tidak |
| Bimbingan DPA (buat, akhiri, alihkan massal) | ya | **mahasiswa di prodi yang ia pimpin** | tidak |
| Unggah dan aktifkan panduan | ya | **prodi yang ia pimpin** | tidak |
| Jejak audit | **ya** | tidak | tidak |

Aturan kode di server: `cakupan.kelola_prodi(prodi_id)` = `superadmin` **atau** `prodi_id` ada di `kaprodi_ids`. Dekan dan kajur punya cakupan **lihat**, bukan **kelola**; praktisnya mereka read-only di halaman admin.

## Cara UI menyembunyikan tombol

1. `isSuper = user.roles.includes('superadmin')` (sudah ada di `StrukturProvider`).
2. `isKaprodi = user.roles.includes('kaprodi')`.
3. **Tombol hanya-superadmin** (ubah struktur, buat/ubah orang, impor, akun, pindah prodi, menu Audit): tampilkan hanya bila `isSuper`.
4. **Tombol kelola-prodi** (daftarkan/ubah keanggotaan, penugasan dosen PA, bimbingan, panduan): tampilkan bila `isSuper || isKaprodi`. Untuk dekan/kajur, sembunyikan tombol dan tampilkan `Alert type="info"` "Peran Anda hanya dapat melihat."
5. **Menyempitkan pilihan prodi untuk kaprodi** (opsional tapi disarankan): ambil `GET /penugasan?orang_id=<user.id>&aktif=true`, saring `peran === 'kaprodi'`, ambil `unit_id`; gunakan sebagai daftar prodi yang boleh dikelola pada `Select` prodi (panduan, keanggotaan, penugasan dosen PA, bimbingan). Bila gagal memuat, jatuh ke semua prodi dan andalkan 403 server. Simpan hasilnya di konteks bersama (mis. `StrukturProvider` menambah `prodiKelola: Set<string> | null`), jangan memanggil ulang di tiap halaman.
6. Jangan membuat salinan logika hak akses server yang rumit di klien. Sedikit saja (peran → tombol); sisanya biarkan server menolak.

## Pesan 403

Tampilkan pesan server apa adanya ("Anda tidak memiliki akses ...") lewat `message.error`. Bukan alasan untuk logout.

## Penjaga rute

`/admin/audit` hanya superadmin: di halaman itu periksa `isSuper`; bila bukan, render `Result status="403"` ("Hanya superadmin yang dapat melihat jejak audit.") dan sembunyikan menunya. Rute lain bisa dibuka semua pengelola.

## Peran yang tidak ada di UI admin

`dosen_pa` murni: tidak punya halaman admin. DPA memutuskan pengajuan di Tasklist AlurKerja (mode AlurKerja) atau lewat API (mode lokal); itu di luar cakupan redesain ini.
