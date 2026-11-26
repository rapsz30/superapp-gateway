"""Sinkron senyap akun dosen ke AlurKerja, supaya tugasnya muncul di Tasklist.

Yang disinkronkan: orang dengan penugasan aktif dosen PA atau kaprodi dan akun aplikasi yang aktif. Hanya menambah:
akun AlurKerja tidak pernah diubah atau dihapus. Yang dikirim hanya nama dan email dosen.

Berjalan berkala di identity bila klien admin dikonfigurasi. Uji coba tanpa membuat apa pun:
    python -m src.domain.akun_alurkerja --coba
"""

from __future__ import annotations

import logging
import sys
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.waktu import hari_ini
from src.db import get_sessionmaker
from src.domain import audit
from src.domain.cakupan import penugasan_aktif
from src.integrations import alurkerja, alurkerja_admin
from src.integrations.alurkerja import AlurKerjaGalat
from src.integrations.alurkerja_admin import AdminGalat, AkunSudahAda
from src.models import Akun, Orang, Penugasan

log = logging.getLogger("identity.akun_alurkerja")

# Email yang sudah dipastikan atau sudah ditangani sejak layanan menyala; tidak ditanyakan lagi.
_selesai: set[str] = set()


def daftar_dosen(db: Session, hari) -> list[tuple[Orang, str]]:
    rows = db.execute(
        select(Orang, Akun.email)
        .join(Akun, Akun.orang_id == Orang.id)
        .join(Penugasan, Penugasan.orang_id == Orang.id)
        .where(Penugasan.peran.in_(("dosen_pa", "kaprodi")), penugasan_aktif(hari), Akun.status == "aktif")
        .distinct()
        .order_by(Orang.nama_lengkap)
    ).all()
    return [(orang, email.strip().lower()) for orang, email in rows]


def sinkron(db: Session, *, coba: bool = False) -> dict[str, list[str]]:
    """Satu putaran. Mengembalikan email per hasil: dibuat, perlu_manual, akan_dibuat, gagal."""
    hasil: dict[str, list[str]] = {"dibuat": [], "perlu_manual": [], "akan_dibuat": [], "gagal": []}
    admin, engine = alurkerja_admin.dapatkan_admin(), alurkerja.dapatkan_klien()
    if engine is None or (admin is None and not coba):
        return hasil
    for orang, email in daftar_dosen(db, hari_ini()):
        if email in _selesai:
            continue
        try:
            if engine.pengguna_ada(email):
                _selesai.add(email)
                continue
            if coba:
                hasil["akan_dibuat"].append(email)
                continue
            terkirim = admin.buat_pengguna(orang.nama_lengkap, email)
        except AkunSudahAda:
            # Akun ada tetapi belum terlihat di engine, biasanya karena dosennya belum pernah masuk ke AlurKerja.
            log.warning("Akun AlurKerja %s sudah ada. Bila tugas tidak muncul setelah ia masuk, cek keanggotaannya di Console.", orang.id)
            _selesai.add(email)
            hasil["perlu_manual"].append(email)
            continue
        except (AlurKerjaGalat, AdminGalat) as exc:
            log.warning("Sinkron akun AlurKerja untuk %s gagal: %s", orang.id, exc)
            hasil["gagal"].append(email)
            continue
        _selesai.add(email)
        hasil["dibuat"].append(email)
        audit.catat(db, None, "alurkerja.akun_dibuat", "orang", orang.id, None, {"email_sandi_terkirim": terkirim})
        db.commit()
        log.info("Akun AlurKerja dibuat untuk %s (email sandi terkirim: %s).", orang.id, terkirim)
    return hasil


def _putaran(jeda: float, berhenti: threading.Event) -> None:
    while not berhenti.wait(jeda):
        try:
            with get_sessionmaker()() as db:
                sinkron(db)
        except Exception:  # putaran berikutnya tetap berjalan
            log.exception("Putaran sinkron akun AlurKerja gagal.")


def mulai_latar() -> threading.Event | None:
    """Jalankan putaran berkala di latar. None bila sinkron tidak dikonfigurasi."""
    if alurkerja_admin.dapatkan_admin() is None or alurkerja.dapatkan_klien() is None:
        return None
    berhenti = threading.Event()
    jeda = max(15, get_settings().alurkerja_sinkron_detik)
    threading.Thread(target=_putaran, args=(jeda, berhenti), daemon=True, name="sinkron-akun-alurkerja").start()
    log.info("Sinkron akun AlurKerja aktif tiap %s detik.", jeda)
    return berhenti


if __name__ == "__main__":
    uji = "--coba" in sys.argv
    s = get_settings()
    if uji and s.alurkerja_admin_client_secret and not s.alurkerja_workspace_id:
        # Bantu mengisi ALURKERJA_WORKSPACE_ID: tampilkan workspace yang ada, tanpa mengubah apa pun.
        calon = alurkerja_admin.AdminKlien(
            s.alurkerja_url, s.alurkerja_keycloak_realm, s.alurkerja_admin_client_id,
            s.alurkerja_admin_client_secret, "", ca_bundle=s.alurkerja_ca_bundle)
        try:
            for w in calon.daftar_workspace():
                print("workspace:", {k: w.get(k) for k in ("id", "name", "slug") if k in w})
        except AdminGalat as exc:
            print(exc)
            sys.exit(1)
    klien = alurkerja_admin.dapatkan_admin()
    if klien is None:
        print("Klien admin belum dikonfigurasi (ALURKERJA_ADMIN_CLIENT_ID/SECRET, ALURKERJA_WORKSPACE_ID).")
    else:
        try:
            klien.masuk()
            print("Klien layanan Keycloak: berhasil masuk.")
        except AdminGalat as exc:
            print(exc)
            sys.exit(1)
    if not uji and klien is None:
        sys.exit(1)
    with get_sessionmaker()() as sesi:
        for nama, daftar in sinkron(sesi, coba=uji).items():
            if daftar:
                print(f"{nama}: {', '.join(daftar)}")
    print("selesai")
