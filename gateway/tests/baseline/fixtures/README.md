# Fixtures Dokumen Uji Fase B (Evaluasi Alur Rekomendasi Matkul)

Folder ini digunakan untuk menyimpan berkas PDF input yang dibutuhkan saat menjalankan pengujian **Fase B** (`powershell -File gateway/tests/baseline/run-baseline.ps1 -Phase B`).

## Berkas yang Dibutuhkan

1. **`khs-sample.pdf`**
   - Berkas PDF Kartu Hasil Studi (KHS) mahasiswa yang memuat daftar mata kuliah yang telah diambil beserta kode mata kuliah, nama mata kuliah, SKS, nilai huruf, dan semester.
   - Digunakan untuk menguji endpoint `POST /api/matkul-recommender/khs/upload` (`multipart/form-data`, field `file`).
   - **WAJIB DIANONIMKAN**: Sebelum meletakkan `khs-sample.pdf` ke dalam folder ini, pastikan seluruh data pribadi (nama mahasiswa, NIM asli, nama Dosen Pembimbing Akademik/DPA, serta tanda tangan/QR code jika ada) telah dihapus atau diganti dengan identitas samaran.

2. **`panduan-sample.pdf`**
   - Berkas PDF buku panduan akademik / kurikulum program studi yang berisi struktur mata kuliah per semester.
   - Digunakan untuk menguji endpoint `POST /api/matkul-recommender/panduan/extract-upload` (`multipart/form-data`, field `file_pdf`).
   - Pastikan berkas PDF memiliki lapisan teks yang dapat diekstrak (*searchable text*, bukan hasil pindaian gambar tanpa OCR).

## Catatan Keamanan & Privasi
- Seluruh berkas `fixtures/*.pdf` telah dimasukkan ke dalam [`gateway/tests/baseline/.gitignore`](../.gitignore) sehingga tidak akan pernah ter-*commit* ke repositori Git.
- Skrip pengujian Fase B dirancang untuk **tidak pernah mencetak isi teks hasil ekstraksi KHS maupun panduan** ke terminal, log, ataupun laporan Markdown.

