# 15. Sinkron akun dosen ke AlurKerja

Tugas AlurKerja ditujukan ke email dosen. Bila email itu belum menjadi pengguna AlurKerja, tugasnya tidak tampil di Tasklist (halaman `/dosen` tetap bisa dipakai). Identity dapat membuat akunnya secara otomatis.

**Dimatikan 26 Nov 2026** atas keputusan pemilik proyek: akun dosen diimpor manual lewat **Console > Users > Import** (CSV berkolom `name`, `email`, `role`; maksimal 200 baris). Secret di `.env` sudah dikosongkan. Impor manual tetap memerlukan perbaikan layanan tenant (butir 2 di bawah).

Riwayat uji sebelum dimatikan:

**Hasil uji 26 Nov 2026:** sempat aktif di instalasi lokal (jeda 60 detik). Akun `daffa@gmail.com` dibuat otomatis (Keycloak). Belum dibuktikan: dosen itu masuk ke AlurKerja dan melihat tugasnya.

Yang diperlukan agar berjalan:

1. Akun layanan `service-account-superapp-sync` harus punya **email** (tanpanya: `token has no email claim`).
2. Layanan `tenant` AlurKerja harus memakai klien rahasia untuk Keycloak Admin. Bawaan instalasi ini memakai klien publik `onprem` sehingga gagal `502 Keycloak is unavailable`. Perbaikan ada di berkas **di luar repo** `release-alurkerja-local/docker-compose.superapp-fix.yml` (klien `integration`, hanya layanan tenant). Menjalankan ulang AlurKerja **tanpa** berkas itu mengembalikan masalahnya:
   `docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.superapp-fix.yml up -d --no-deps tenant`
3. Engine baru mengenal pengguna setelah ia masuk (tombol Sync di Studio butuh lisensi aktif: `LICENSE_NOT_ACTIVATED`). Karena itu setelah identity menyala ulang, akun yang belum pernah masuk dicoba lagi sekali, dijawab 409, lalu dibiarkan.

Mailpit instalasi lokal: http://localhost:8105/mailpit/

## Perilaku

- Tiap `ALURKERJA_SINKRON_DETIK` (bawaan 60) identity memeriksa orang dengan penugasan aktif **dosen PA atau kaprodi** dan akun aplikasi aktif.
- Sudah ada di engine (`GET /engine-rest/user?id=<email>`): dilewati.
- Belum ada: `POST /api/v1/tenant/admin/users` dengan `name`, `email`, `workspace_id`, `role: member`. AlurKerja mengirim email pengaturan sandi (instalasi lokal: Mailpit, http://localhost:8105/mailpit/).
- Konflik (akun sudah ada): dicatat di log; tambahkan ke workspace lewat Console bila tugas tidak muncul.
- Gagal: dicoba lagi pada putaran berikutnya.
- Hanya menambah; tidak pernah mengubah atau menghapus akun. Tercatat di audit `alurkerja.akun_dibuat`.

API admin itu **tidak terdokumentasi publik** dan bisa berubah saat AlurKerja diperbarui.

## Risiko

Peran `platform_owner` mencakup seluruh instalasi AlurKerja, bukan satu workspace. Simpan rahasianya hanya di `services/identity/.env`, jangan di repo. Untuk menonaktifkan: kosongkan `ALURKERJA_ADMIN_CLIENT_SECRET` atau nonaktifkan klien di Keycloak.

## Pengaturan (dilakukan admin AlurKerja)

1. Keycloak Admin (`https://alurkerja.local:8100/sso/admin/`), realm **alurkerja** > Clients > Create client. Client ID `superapp-sync`; **Client authentication** On; hanya **Service accounts roles** yang dicentang.
2. Klien itu > **Service accounts roles** > Assign role > realm role **platform_owner**.
3. Bila uji di bawah ditolak dengan 403: Client scopes > `superapp-sync-dedicated` > tambah mapper **User Realm Role**, Token Claim Name `roles`, Multivalued On, masuk access token.
4. Tab **Credentials**: salin Client secret.
5. Isi di `services/identity/.env`: `ALURKERJA_ADMIN_CLIENT_ID=superapp-sync`, `ALURKERJA_ADMIN_CLIENT_SECRET=...`, `ALURKERJA_WORKSPACE_ID=...` (id workspace StudentGateway, lihat di Console > Workspaces).
6. Muat ulang identity, lalu uji **tanpa membuat akun**:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d identity-api
```

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec nginx nginx -s reload
```

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec identity-api python -m src.domain.akun_alurkerja --coba
```

Layanan yang menyala dengan konfigurasi lengkap **langsung** menyinkronkan pada putaran pertama (setelah satu jeda). Untuk memeriksa dulu, set `ALURKERJA_SINKRON_DETIK=86400` saat uji pertama, lalu kembalikan.
