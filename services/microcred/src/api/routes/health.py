from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter
from sqlalchemy import text
from src.core.config import get_settings
from src.infrastructure.db.session import get_session_factory

router = APIRouter(tags=["Observability"])
logger = structlog.get_logger()


async def check_postgres() -> dict:
    """Check PostgreSQL connection."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)[:100]}


async def check_redis() -> dict:
    """Check Redis connection."""
    try:
        import redis.asyncio as aioredis

        settings = get_settings()
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)[:100]}


@router.get("/health", summary="Service health probe")
async def health_check() -> dict:
    """Return basic service and datastore status information."""
    settings = get_settings()

    # Check actual connections
    postgres_status = await check_postgres()
    redis_status = await check_redis()

    # Overall status is ok only if all datastores are ok
    overall_status = "ok"
    if postgres_status.get("status") != "ok" or redis_status.get("status") != "ok":
        overall_status = "degraded"

    payload = {
        "service": settings.app_name,
        "version": settings.version,
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "datastores": {
            "postgres": postgres_status,
            "redis": redis_status,
        },
    }
    logger.info("health_probe", **payload)
    return payload
