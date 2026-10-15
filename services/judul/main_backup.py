# =================================================================
# 1. IMPOR LIBRARY YANG DIBUTUHKAN
# =================================================================
import os
import json
import prompt_eng
from groq import Groq
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# =================================================================
# 2. INISIALISASI & KONFIGURASI AWAL
# =================================================================
load_dotenv()

# Inisialisasi klien Groq dengan API Key
try:
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
except Exception as e:
    print(f"Error konfigurasi Groq: {e}")

app = FastAPI(
    title="Rekomendasi Judul Tugas Akhir (Groq Llama3)",
    description="API untuk mendapatkan rekomendasi judul TA menggunakan Groq Llama3.",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# 3. DEFINISI MODEL DATA (REQUEST BODY)
# =================================================================


class UserInput(BaseModel):
    interests: str

# =================================================================
# 4. FUNGSI UNTUK MEMBUAT PROMPT
# =================================================================


# def create_prompt(interests: str):
#     return f"""
#     Anda adalah seorang asisten ahli akademis di bidang informatika yang sangat berpengalaman. Tugas Anda adalah memberikan 3 rekomendasi judul tugas akhir yang inovatif, relevan, dan layak dikerjakan oleh mahasiswa S1 berdasarkan minat yang mereka berikan.

#     Minat Mahasiswa: "{interests}"

#     Berikan 3 rekomendasi. Untuk setiap rekomendasi, wajib sertakan:
#     1.  **judul**: Sebuah judul tugas akhir yang jelas, spesifik, dan menarik.
#     2.  **deskripsi**: Penjelasan singkat dalam 2-3 kalimat. Jelaskan masalah yang ingin diselesaikan, tujuan dari penelitian, dan output yang diharapkan.
#     3.  **metodologi**: Jelaskan metodologi dalam penelitian tersebut.
#     4.  **referensi**: Berikan 2 contoh referensi jurnal ilmiah atau artikel konferensi internasional yang relevan dan bisa menjadi landasan literatur. Tulis dalam format sitasi standar (contoh: APA) dan pastikan terdapat link yang menuju jurnal tersebut.

#     ================================
#     ATURAN SANGAT PENTING UNTUK REFERENSI:
#     - Anda HARUS memberikan referensi yang NYATA dan dapat diverifikasi. JANGAN MENGARANG atau MENGHASILKAN REFERENSI FIKTIF (HALUSINASI).
#     - Untuk setiap referensi, formatnya HARUS berupa objek JSON dengan dua kunci: "sitasi" dan "link".
#     - Kunci "sitasi" berisi sitasi lengkap dalam format APA.
#     - Kunci "link" HARUS berisi URL valid yang mengarah langsung ke halaman artikel, diutamakan dari Google Scholar, IEEE Xplore, atau ACM Digital Library.
#     - Jika Anda sama sekali tidak dapat menemukan link langsung yang valid, isi kunci "link" dengan string "Tidak ditemukan link langsung, verifikasi manual di Google Scholar.".
#     - Integritas akademis adalah prioritas utama.

#     Contoh format referensi yang baik:
#     "referensi": [
#         {{
#             "sitasi": "He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. In Proceedings of the IEEE conference on computer vision and pattern recognition (pp. 770-778).",
#             "link": "https://doi.org/10.1109/CVPR.2016.90"
#         }},
#         {{
#             "sitasi": "Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. In Advances in neural information processing systems (pp. 5998-6008).",
#             "link": "https://scholar.google.com/scholar?cluster=8533923985724213941"
#         }}
#     ]
#     ================================

#     Gunakan bahasa indonesia untuk menjawabnya.

#     PENTING: Seluruh output Anda HARUS dalam format JSON yang valid dan bersih.
#     JAWAB LANGSUNG HANYA DENGAN BLOK JSON, tanpa teks pembuka atau basa-basi apa pun. Kunci utama JSON harus bernama "rekomendasi".
#     """

# =================================================================
# 5. ENDPOINT UTAMA API
# =================================================================


@app.post("/get-recommendations")
async def get_recommendations(user_input: UserInput):
    """
    Endpoint ini menerima minat mahasiswa dan mengembalikan 3 rekomendasi TA.
    """
    try:
        # Validasi input untuk memastikan tidak kosong
        if not user_input.interests or not user_input.interests.strip():
            raise HTTPException(
                status_code=400, detail="Input 'interests' tidak boleh kosong.")

        # 1. Buat prompt lengkap berdasarkan input pengguna
        prompt = create_prompt(user_input.interests)

        # 2. Kirim prompt ke model Llama3 via Groq
        chat_completion = client.chat.completions.create(
            # --- BAGIAN YANG DIPERBAIKI ---
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            # ---------------------------
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
        )

        # 3. Ambil konten respons dari AI
        response_content = chat_completion.choices[0].message.content

        # 4. Ubah string JSON menjadi dictionary Python
        recommendations = json.loads(response_content)

        # 5. Kembalikan hasil yang sudah rapi
        return recommendations

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Gagal mem-parsing respons dari AI. Coba lagi.")
    except Exception as e:
        print(f"Terjadi error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Terjadi kesalahan internal: {e}")
