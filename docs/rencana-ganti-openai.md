# Rencana: Ganti Groq ke OpenAI (Layanan Rekomendasi Judul)

Dokumen serah terima untuk agen pelaksana. Ditulis 27 Nov 2026. **Belum ada kode yang diubah untuk rencana ini.**

Permintaan pemilik: layanan rekomendasi judul memakai **OpenAI**, bukan Groq (pemilik menulis "grokapi"). Pekerjaan ini **terpisah** dari [rencana registrasi](rencana-registrasi-sederhana.md) dan tidak bergantung padanya.

## 1. Aturan kerja (wajib)

1. Repo `superapp-gateway`, branch `feat/hackathon-superapp-gateway`. **Jangan commit atau push** tanpa diminta pemilik proyek.
2. Folder kerja dapat berisi **perubahan belum di-commit** milik pemilik atau agen lain (misalnya pekerjaan registrasi). Bangun di atasnya. Jangan `git checkout`, `reset`, `stash`, atau menimpa berkas secara utuh.
3. Jangan membaca, mencetak, atau menulis kunci API, sandi, atau isi `.env` ke kode, dokumen, log, atau keluaran.
4. Kerjakan dan uji di lokal saja. **Jangan deploy** tanpa diminta; sekarang masa presentasi (27 Nov–1 Des 2026).
5. Komunikasi dengan pemilik proyek dalam bahasa Indonesia.

## 2. Keadaan sekarang

- Hanya `services/judul` yang memakai Groq (model `openai/gpt-oss-20b` yang dijalankan di Groq). Matkul, microcred, dan connector sudah memakai OpenAI.
- Dua pemanggilan: `services/ai_service.py` (`_call_groq_api`, rekomendasi judul) dan `services/obrolan_service.py` (brainstorm).
- Identity memanggil layanan judul lewat `JUDUL_URL`; kontrak HTTP-nya **tidak berubah**, jadi identity, gateway, web, dan BPMN tidak perlu disentuh.

## 3. Perubahan kode

| Berkas | Perubahan |
|---|---|
| `services/judul/config/settings.py` | `GROQ_API_KEY` → `OPENAI_API_KEY`; `GROQ_MODEL` → `OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")` (sama dengan bawaan matkul); `get_groq_client` → `get_openai_client` mengembalikan `OpenAI(api_key=..., timeout=35.0, max_retries=1)`; perbarui deskripsi API |
| `services/judul/services/ai_service.py` | impor `APIConnectionError`, `BadRequestError` dari `openai`; ganti nama `_call_groq_api` dan pesan log |
| `services/judul/services/obrolan_service.py` | impor dari `openai`; klien dan model baru |
| kedua pemanggilan | **hapus `extra_body={"reasoning_effort": "low"}`**. Parameter itu untuk model penalaran; `gpt-4o-mini` menolaknya, sehingga setiap percobaan gagal |
| kedua pemanggilan | pertahankan `response_format={"type": "json_object"}` (prompt sudah menyebut JSON), `temperature`, `max_completion_tokens`, dan batas waktu (harus selesai sebelum 55–60 detik klien identity dan gateway) |
| `services/judul/requirements.txt` | ganti `groq==0.29.0` dengan `openai==<versi stabil yang dipatok>`, cocok dengan `httpx==0.28.1` dan `pydantic==2.11.7`. **Berkas ber-encoding UTF-16 LE dengan BOM**; pertahankan, jangan sampai rusak saat disunting |
| `services/judul/.env.example` | `OPENAI_API_KEY=` dan `OPENAI_MODEL=gpt-4o-mini`; hapus baris Groq |
| `deploy/deploy-vps.sh` | pemeriksaan wajib `services/judul/.env GROQ_API_KEY` → `OPENAI_API_KEY` |
| `deploy/isi-env.py` | pertanyaan "Kunci Groq" → `OPENAI_API_KEY` untuk judul |
| `.github/workflows/ci.yml` | berkas env tiruan judul memakai `OPENAI_API_KEY` dummy (muncul di dua tempat) |
| `docs/deploy-vps.md`, `docs/identity/14-pengajuan-judul-ta.md`, `docs/ci-cd.md` | perbarui penyebutan. Laporan hasil uji lama di `docs/` adalah catatan sejarah, **jangan diubah** |

Berkas lama `main_backup.py`, `app_frontend.py`, `test_all.py`, `test_api_key.py`, dan `report.txt` masih menyebut Groq. Sesuaikan yang masih berguna (`test_api_key.py` mencetak potongan kunci: jangan jalankan, dan ubah agar hanya menyatakan terisi atau tidak). Jangan hapus berkas tanpa izin pemilik.

## 4. Kunci API

Pemilik yang mengisi kunci; agen tidak membaca, mencetak, atau menyalin isinya ke keluaran.

- Lokal: `services/judul/.env` perlu `OPENAI_API_KEY`.
- Server (saat deploy diminta): isi `~/superapp/env/services/judul/.env` **sebelum** deploy, kalau tidak skrip deploy membatalkan. Salin juga `isi-env.py` versi baru ke `~/superapp/` bila akan dipakai lagi. Biarkan `GROQ_API_KEY` lama sampai deploy berhasil, supaya rilis sebelumnya masih bisa dipulihkan.

## 5. Pengujian

1. `docker compose build judul-api` berhasil; tidak ada impor `groq` tersisa di jalur yang dijalankan `main.py`.
2. Dengan kunci asli (diisi pemilik): `/get-recommendations` dan `/chat` lewat web menghasilkan JSON sah; tema berasal dari daftar; selesai di bawah 55 detik. Uji beberapa kali, termasuk membahas satu kandidat dan meminta judul diubah (`usulan`).
3. Bandingkan mutu bahasa Indonesia dan format "saran" dengan hasil sebelumnya; model berbeda bisa memberi gaya berbeda. Laporkan, jangan ubah prompt besar-besaran tanpa persetujuan.
4. Uji identity untuk judul tetap lulus.
5. Panggilan berbayar: lakukan seperlunya dan sebutkan jumlahnya di laporan.

## 6. Selesai bila

- [ ] Rekomendasi dan brainstorm berjalan dengan OpenAI di lokal.
- [ ] Skrip deploy, pengisi env, CI, contoh env, dan dokumen tidak lagi mensyaratkan Groq.
- [ ] Tidak ada kunci di kode atau keluaran.

Catatan untuk pemilik: seluruh pemakaian AI akan masuk satu tagihan OpenAI, sehingga registrasi publik menaikkan biaya dan berbagi batas laju yang sama.
