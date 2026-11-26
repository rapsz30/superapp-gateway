#!/usr/bin/env python3
"""Isi berkas .env superapp di server. Dijalankan DI SERVER, setelah `deploy-vps.sh siapkan`:

    python3 ~/superapp/isi-env.py

Rahasia internal dibuat acak; kunci AI dan akun layanan AlurKerja Anda ketik sendiri (tidak tampil di layar).
Aman diulang: nilai yang sudah terisi tidak diganti (Enter untuk mempertahankan). Tidak ada nilai yang dicetak.
"""

from __future__ import annotations

import base64
import getpass
import re
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ALURKERJA_URL = "https://alurkerja.ahlanapp.cloud"
TENANT_LIVE = "3d84b499-09c2-4288-b3bb-7d9e83e4fdbe"
DASAR = Path(__file__).resolve().parent / "env"
CONTOH = ("ganti", "replace", "postgres-password", "change-me")


class Env:
    def __init__(self, jalur: str) -> None:
        self.jalur = DASAR / jalur
        if not self.jalur.is_file():
            sys.exit(f"Belum ada {self.jalur}. Jalankan 'deploy-vps.sh siapkan' dari laptop dulu.")
        self.baris = self.jalur.read_text(encoding="utf-8").splitlines()

    def ambil(self, kunci: str) -> str:
        for b in self.baris:
            if b.startswith(kunci + "="):
                return b.split("=", 1)[1].strip().strip("'\"")
        return ""

    def kosong(self, kunci: str) -> bool:
        v = self.ambil(kunci)
        return not v or any(c in v.lower() for c in CONTOH)

    def set(self, kunci: str, nilai: str) -> None:
        # Kutip tunggal agar tanda $ atau # tidak ditafsirkan Docker Compose.
        if not re.fullmatch(r"[A-Za-z0-9_@%+=:,./?-]*", nilai):
            nilai = f"'{nilai}'"
        baru = f"{kunci}={nilai}"
        for i, b in enumerate(self.baris):
            if b.startswith(kunci + "="):
                self.baris[i] = baru
                return
        self.baris.append(baru)

    def simpan(self) -> None:
        self.jalur.write_text("\n".join(self.baris) + "\n", encoding="utf-8", newline="\n")
        self.jalur.chmod(0o600)


def tanya(env: Env, kunci: str, label: str, rahasia: bool = True) -> str:
    ada = not env.kosong(kunci)
    petunjuk = " [Enter = pakai yang sudah ada]" if ada else ""
    while True:
        isi = (getpass.getpass if rahasia else input)(f"{label}{petunjuk}: ").strip()
        if "'" in isi:
            print("  Tidak boleh memuat tanda kutip tunggal.")
        elif isi:
            env.set(kunci, isi)
            return isi
        elif ada:
            return env.ambil(kunci)
        else:
            print("  Wajib diisi.")


def uji_camunda(pengguna: str, sandi: str) -> str:
    kepala = {"Authorization": "Basic " + base64.b64encode(f"{pengguna}:{sandi}".encode()).decode()}
    url = f"{ALURKERJA_URL}/engine-rest/process-definition/count?tenantIdIn={TENANT_LIVE}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=kepala), timeout=20) as r:
            badan = r.read().decode()
    except urllib.error.HTTPError as e:
        return f"GAGAL: AlurKerja menjawab {e.code}. Periksa nama pengguna, sandi, dan grup akunnya."
    except OSError as e:
        return f"GAGAL: AlurKerja tidak terjangkau ({type(e).__name__})."
    jumlah = re.search(r'"count"\s*:\s*(\d+)', badan)
    if not jumlah or int(jumlah.group(1)) < 2:
        return "GAGAL: akun masuk, tetapi tidak melihat kedua proses Live. Masukkan ke grup camunda-admin."
    return "OK: akun layanan masuk dan melihat proses Live."


def main() -> None:
    identity = Env("services/identity/.env")
    matkul = Env("services/matkul/.env.local")
    micro = Env("services/microcred/.env")
    judul = Env("services/judul/.env")
    konektor = Env("alurkerja-connector/.env")

    def acak(env: Env, kunci: str, byte: int = 32) -> str:
        if env.kosong(kunci):
            env.set(kunci, secrets.token_hex(byte))
        return env.ambil(kunci)

    # Rahasia internal (dibuat acak).
    for env, skema, host, nama in (
        (identity, "postgresql+psycopg2", "identity-db", "identity"),
        (matkul, "postgresql", "matkul-db", "matkul"),
        (micro, "postgresql+asyncpg", "db", "microcred"),
    ):
        sandi = acak(env, "POSTGRES_PASSWORD", 24)
        env.set("DATABASE_URL", f"{skema}://{nama}:{sandi}@{host}:5432/{nama}")
    acak(identity, "JWT_SECRET")
    acak(micro, "JWT_SECRET")
    micro.set("APP_ENV", "production")
    internal = acak(identity, "INTERNAL_TOKEN")
    matkul.set("INTERNAL_TOKEN", internal)
    layanan = acak(identity, "MATKUL_SERVICE_TOKEN")
    matkul.set("MATKUL_SERVICE_TOKEN", layanan)
    konektor.set("GATEWAY_TOKEN", layanan)
    if matkul.kosong("PB_ADMIN_EMAIL"):
        matkul.set("PB_ADMIN_EMAIL", "admin@superapp.example.com")
    acak(matkul, "PB_ADMIN_PASSWORD", 24)

    # Alamat AlurKerja (bukan rahasia).
    identity.set("ALURKERJA_URL", ALURKERJA_URL)
    identity.set("ALURKERJA_TENANT_ID", TENANT_LIVE)
    identity.set("ALURKERJA_CA_BUNDLE", "")
    konektor.set("ALURKERJA_BASE_URL", ALURKERJA_URL)
    konektor.set("LLM_PROVIDER", "openai")
    konektor.set("LLM_MODEL", "gpt-4o-mini")

    print("Rahasia internal sudah dibuat. Sekarang yang harus Anda ketik (tidak tampil di layar).\n")
    tanya(matkul, "OPENAI_API_KEY", "Kunci OpenAI")
    tanya(judul, "GROQ_API_KEY", "Kunci Groq")
    print("\nAkun layanan Camunda untuk superapp:")
    pengguna = tanya(identity, "ALURKERJA_USERNAME", "  Nama pengguna", rahasia=False)
    sandi = tanya(identity, "ALURKERJA_PASSWORD", "  Sandi")
    konektor.set("ALURKERJA_ET_USERNAME", pengguna)
    konektor.set("ALURKERJA_ET_PASSWORD", sandi)

    for env in (identity, matkul, micro, judul, konektor):
        env.simpan()
    print("\nTersimpan di", DASAR)
    print(uji_camunda(pengguna, sandi))


if __name__ == "__main__":
    main()
