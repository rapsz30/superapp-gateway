"""Fixture uji. Memakai Postgres sungguhan (bukan SQLite), karena indeks unik parsial,
CHECK, dan trigger audit adalah bagian dari perilaku yang diuji.

Database uji: env TEST_DATABASE_URL, bawaan postgresql+psycopg2://identity:identity@127.0.0.1:55433/identity_test
Jalankan: docker run -d --name identity-test-db -e POSTGRES_USER=identity -e POSTGRES_PASSWORD=identity \
  -e POSTGRES_DB=identity_test -p 127.0.0.1:55433:5432 postgres:15.5
"""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterator
from datetime import date

import pytest

URL_UJI = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://identity:identity@127.0.0.1:55433/identity_test",
)
os.environ["DATABASE_URL"] = URL_UJI
os.environ["JWT_SECRET"] = "x" * 48
os.environ["BCRYPT_ROUNDS"] = "4"
INTERNAL_TOKEN = "t" * 40
os.environ["INTERNAL_TOKEN"] = INTERNAL_TOKEN
os.environ["MATKUL_SERVICE_TOKEN"] = "m" * 40
# Uji tidak boleh menyentuh AlurKerja sungguhan, apa pun isi lingkungan pengembang. Diisi kosong (bukan
# dihapus) karena variabel lingkungan yang kosong mengalahkan nilai dari berkas .env.
for _k in ("ALURKERJA_URL", "ALURKERJA_USERNAME", "ALURKERJA_PASSWORD", "ALURKERJA_CA_BUNDLE",
           "ALURKERJA_AUTH_TOKEN_SLUG", "ALURKERJA_CLIENT_ID", "ALURKERJA_CLIENT_SECRET", "ALURKERJA_DASHBOARD_RINGKASAN",
           "ALURKERJA_DASHBOARD_MATKUL", "ALURKERJA_DASHBOARD_JUDUL",
           "ALURKERJA_ADMIN_CLIENT_ID", "ALURKERJA_ADMIN_CLIENT_SECRET", "ALURKERJA_WORKSPACE_ID"):
    os.environ[_k] = ""
os.environ["PANDUAN_DIR"] = tempfile.mkdtemp(prefix="identity-panduan-")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.api.deps import reset_semua_pembatas  # noqa: E402
from src.api.main import app  # noqa: E402
from src.core.security import hash_sandi  # noqa: E402
from src.db import get_engine, get_sessionmaker  # noqa: E402
from src.models import Akun, Orang, Penugasan  # noqa: E402

SANDI = "sandi-uji-12345"


@pytest.fixture(scope="session", autouse=True)
def _skema() -> Iterator[None]:
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _bersih(_skema) -> Iterator[None]:
    tabel = (
        "audit_log, refresh_token, pengajuan, bimbingan, keanggotaan_prodi, penugasan, panduan_akademik, "
        "akun, orang, prodi, jurusan, fakultas"
    )
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tabel} RESTART IDENTITY CASCADE"))
    reset_semua_pembatas()
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with get_sessionmaker()() as s:
        yield s


def buat_orang_akun(
    db,
    nama: str,
    email: str,
    *,
    peran: str | None = None,
    unit_tipe: str = "global",
    unit_id: uuid.UUID | None = None,
    sandi: str = SANDI,
    wajib_ganti: bool = False,
    nim: str | None = None,
    nidn: str | None = None,
) -> Orang:
    o = Orang(nama_lengkap=nama, nim=nim, nidn=nidn)
    db.add(o)
    db.flush()
    db.add(
        Akun(orang_id=o.id, email=email, sandi_hash=hash_sandi(sandi), wajib_ganti_sandi=wajib_ganti)
    )
    if peran:
        db.add(
            Penugasan(
                orang_id=o.id, peran=peran, unit_tipe=unit_tipe, unit_id=unit_id, mulai=date(2020, 1, 1)
            )
        )
    db.commit()
    return o


def masuk(client: TestClient, email: str, sandi: str = SANDI) -> dict[str, str]:
    r = client.post("/auth/login", json={"email": email, "sandi": sandi})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client, db) -> dict[str, str]:
    buat_orang_akun(db, "Super Admin", "admin@kampus.ac.id", peran="superadmin")
    return masuk(client, "admin@kampus.ac.id")


@pytest.fixture
def kampus(client, admin) -> dict:
    """Satu fakultas, satu jurusan, dua prodi."""
    f = client.post("/fakultas", json={"kode": "FTI", "nama": "Fakultas Teknologi Industri"}, headers=admin).json()
    j = client.post(
        "/jurusan", json={"fakultas_id": f["id"], "kode": "IF", "nama": "Informatika"}, headers=admin
    ).json()
    p1 = client.post(
        "/prodi", json={"jurusan_id": j["id"], "kode": "IF-S1", "nama": "Informatika", "jenjang": "S1"},
        headers=admin,
    ).json()
    p2 = client.post(
        "/prodi", json={"jurusan_id": j["id"], "kode": "IF-IP", "nama": "Informatika Internasional", "jenjang": "S1"},
        headers=admin,
    ).json()
    return {"fakultas": f, "jurusan": j, "prodi1": p1, "prodi2": p2}


def buat_pdf(baris: list[str] | None) -> bytes:
    """PDF sederhana berisi teks (atau kosong bila baris None, meniru hasil scan)."""
    if baris is None:
        isi_stream = b"q 10 10 100 100 re S Q"
    else:
        potongan = ["BT /F1 11 Tf 40 780 Td 14 TL"]
        for b in baris:
            aman = b.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            potongan.append(f"({aman}) Tj T*")
        potongan.append("ET")
        isi_stream = "\n".join(potongan).encode("latin-1")
    objek = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(isi_stream)).encode() + b" >>\nstream\n" + isi_stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offset = []
    for i, o in enumerate(objek, start=1):
        offset.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objek) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offset:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objek) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


TEKS_PANDUAN = [
    "Buku Panduan Akademik Program Studi Informatika",
    "Beban studi maksimal semester 3 adalah 24 SKS bagi mahasiswa dengan IPK 3,00 ke atas.",
    "Mata kuliah wajib semester 3: Struktur Data (3 SKS), Basis Data (3 SKS), Aljabar Linear (3 SKS).",
    "Mata kuliah dengan nilai D atau E wajib diulang pada semester berikutnya yang ditawarkan.",
]
PDF_PANDUAN = buat_pdf(TEKS_PANDUAN)
