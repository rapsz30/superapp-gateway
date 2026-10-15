import streamlit as st
import requests
import json

# URL dari backend FastAPI. Pastikan backend sedang berjalan.
BACKEND_URL = "http://127.0.0.1:8000/get-recommendations"

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="Rekomendasi Tugas Akhir AI",
    page_icon="🤖",
    layout="wide"
)

# --- Tampilan Antarmuka (UI) ---
st.title("🤖 Asisten AI Rekomendasi Judul Tugas Akhir")
st.caption("Ditenagai oleh Llama3 via Groq, FastAPI, & Streamlit")

# Membuat form agar aplikasi tidak me-refresh setiap kali user mengetik
with st.form("input_form"):
    # Kotak input untuk minat pengguna
    user_interests = st.text_area(
        "Masukkan topik, bidang, atau minat Anda di sini:",
        "contoh: sistem deteksi kantuk untuk pengemudi menggunakan computer vision dan machine learning",
        height=150
    )

    # Tombol untuk mengirim permintaan
    submitted = st.form_submit_button("Dapatkan Rekomendasi")

# --- Logika Setelah Tombol Ditekan ---
if submitted:
    if not user_interests.strip():
        st.warning("Mohon masukkan minat Anda terlebih dahulu.")
    else:
        # Tampilkan spinner "loading" saat menunggu respons
        with st.spinner("AI sedang meracik ide-ide brilian untuk Anda... 🧠"):
            try:
                # Siapkan data untuk dikirim ke backend
                payload = {"interests": user_interests}

                # Kirim request POST ke backend
                response = requests.post(BACKEND_URL, json=payload)

                # Periksa apakah request berhasil (status code 200)
                if response.status_code == 200:
                    data = response.json()
                    st.success(
                        "Berikut 3 rekomendasi yang berhasil dibuatkan!")

                    # Tampilkan setiap rekomendasi
                    for i, rec in enumerate(data.get("rekomendasi", [])):

                        st.markdown("**Referensi Akademik (Verified):**")
                        for j, ref in enumerate(rec.get("referensi", [])):
                            # Check if ref is dict (new format) or string (old format)
                            if isinstance(ref, dict):
                                sitasi = ref.get("sitasi", "")
                                link = ref.get("link", "")

                                # Display dengan link clickable
                                st.markdown(f"{j+1}. {sitasi}")
                                st.markdown(f"   🔗 [Akses Paper]({link})")
                            else:
                                # Fallback untuk format lama (string)
                                st.text(f"{j+1}. {ref}")

                            st.markdown("")  # Spacing
                        st.subheader(
                            f"Rekomendasi #{i+1}: {rec.get('judul', 'Tanpa Judul')}")
                        with st.container(border=True):
                            st.markdown(
                                f"**Deskripsi:**\n{rec.get('deskripsi', '')}")
                            st.markdown(
                                f"**Metodologi yang disarankan:**\n{rec.get('metodologi', '')}")

                            st.markdown("**Referensi Awal:**")
                            for ref in rec.get("referensi", []):
                                st.text(f"- {ref}")
                else:
                    # Tampilkan pesan error jika backend tidak merespons dengan baik
                    st.error(
                        f"Gagal menghubungi server. Status: {response.status_code}")
                    st.text(f"Detail: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error(
                    "Gagal terhubung ke server backend. Pastikan server FastAPI (uvicorn) sedang berjalan.")
            except Exception as e:
                st.error(f"Terjadi kesalahan tak terduga: {e}")
# --- WITH DEBUGGING PRINTS ADDED ---
if submitted:
    if not user_interests.strip():
        st.warning("Mohon masukkan minat Anda terlebih dahulu.")
    else:
        with st.spinner("AI sedang meracik ide-ide brilian untuk Anda... 🧠"):
            try:
                payload = {"interests": user_interests}

                # ADD THIS: Debug print
                st.write(f"🔍 Debug: Sending request to {BACKEND_URL}")
                st.write(f"📦 Debug: Payload = {payload}")

                response = requests.post(BACKEND_URL, json=payload)

                # ADD THIS: Debug response
                st.write(f"📡 Debug: Status code = {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    st.success(
                        "Berikut 3 rekomendasi yang berhasil dibuatkan!")
                    # ... rest of code
                else:
                    st.error(
                        f"Gagal menghubungi server. Status: {response.status_code}")
                    st.text(f"Detail: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error(
                    "Gagal terhubung ke server backend. Pastikan server FastAPI (uvicorn) sedang berjalan.")
            except Exception as e:
                st.error(f"Terjadi kesalahan tak terduga: {e}")
