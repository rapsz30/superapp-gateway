from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from src.api.deps import DB, Hal, Superadmin
from src.api.schemas import AuditOut
from src.models import AuditLog

router = APIRouter(tags=["audit"])


@router.get("/audit")
def daftar_audit(
    _: Superadmin,
    db: DB,
    hal: Hal,
    objek_id: uuid.UUID | None = None,
    pelaku_id: uuid.UUID | None = None,
    aksi: str | None = None,
    dari: datetime | None = None,
    sampai: datetime | None = None,
) -> dict:
    q = select(AuditLog)
    if objek_id:
        q = q.where(AuditLog.objek_id == objek_id)
    if pelaku_id:
        q = q.where(AuditLog.pelaku_id == pelaku_id)
    if aksi:
        q = q.where(AuditLog.aksi == aksi)
    if dari:
        q = q.where(AuditLog.waktu >= dari)
    if sampai:
        q = q.where(AuditLog.waktu <= sampai)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(AuditLog.id.desc()).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [AuditOut.model_validate(r) for r in rows], "total": total}
