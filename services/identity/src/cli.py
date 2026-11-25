"""Perintah administrasi. Pemakaian:

    python -m src.cli buat-superadmin --email admin@kampus.ac.id --nama "Nama Admin"

Sandi sementara dicetak sekali. Akun wajib mengganti sandi saat login pertama.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from src.core.security import hash_sandi, sandi_acak, validasi_kebijakan_sandi
from src.core.waktu import hari_ini
from src.db import get_sessionmaker
from src.domain import audit
from src.models import Akun, Orang, Penugasan


def buat_superadmin(email: str, nama: str, sandi: str | None) -> str:
    email = email.strip().lower()
    dibuat_otomatis = sandi is None
    sandi = sandi or sandi_acak()
    pesan = validasi_kebijakan_sandi(sandi, email)
    if pesan:
        raise SystemExit(pesan)

    with get_sessionmaker()() as db:
        if db.scalar(select(func.count()).select_from(Akun).where(func.lower(Akun.email) == email)):
            raise SystemExit("Email sudah dipakai.")
        orang = Orang(nama_lengkap=nama.strip(), email_kontak=email)
        db.add(orang)
        db.flush()
        akun = Akun(orang_id=orang.id, email=email, sandi_hash=hash_sandi(sandi), wajib_ganti_sandi=True)
        db.add(akun)
        db.add(
            Penugasan(
                orang_id=orang.id, peran="superadmin", unit_tipe="global", unit_id=None, mulai=hari_ini()
            )
        )
        db.flush()
        audit.catat(db, None, "akun.buat_superadmin", "akun", akun.id, None, audit.ke_dict(akun))
        db.commit()
    return sandi if dibuat_otomatis else "(sandi sesuai argumen --sandi)"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="identity")
    sub = parser.add_subparsers(dest="perintah", required=True)
    p = sub.add_parser("buat-superadmin", help="Buat akun superadmin pertama")
    p.add_argument("--email", required=True)
    p.add_argument("--nama", required=True)
    p.add_argument("--sandi", help="Bila kosong, dibuat acak dan dicetak sekali")
    args = parser.parse_args(argv)

    if args.perintah == "buat-superadmin":
        sandi = buat_superadmin(args.email, args.nama, args.sandi)
        print(f"Superadmin dibuat: {args.email.strip().lower()}")
        print(f"Sandi sementara : {sandi}")
        print("Akun wajib mengganti sandi saat login pertama.")


if __name__ == "__main__":
    main(sys.argv[1:])
