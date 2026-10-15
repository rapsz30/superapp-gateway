from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from src.api.deps import get_db_session
from src.api.main import app
from src.core.auth import create_access_token
from src.domain.reference_data import QUESTION_TEMPLATES, ROLE_DEFINITIONS
from src.infrastructure.db.base import Base
from src.infrastructure.db.models import (
    QuestionTemplate,
    RoleCatalog,
)


@pytest.fixture()
def test_client(event_loop: asyncio.AbstractEventLoop) -> Iterator[TestClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _init_db() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            await seed_reference_data(session, include_questions=False)

    event_loop.run_until_complete(_init_db())

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as client:
        # Store engine and session_factory for use in other fixtures
        client.engine = engine  # type: ignore
        client.session_factory = session_factory  # type: ignore
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    event_loop.run_until_complete(engine.dispose())


@pytest.fixture()
def test_client_with_questions(event_loop: asyncio.AbstractEventLoop) -> Iterator[TestClient]:
    """Test client with full seed data including question templates."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _init_db() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            await seed_reference_data(session, include_questions=True)

    event_loop.run_until_complete(_init_db())

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as client:
        client.engine = engine  # type: ignore
        client.session_factory = session_factory  # type: ignore
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    event_loop.run_until_complete(engine.dispose())


async def seed_reference_data(session: AsyncSession, include_questions: bool = False) -> None:
    role_count = await session.scalar(select(RoleCatalog.id).limit(1))
    if role_count:
        return

    for role in ROLE_DEFINITIONS:
        session.add(RoleCatalog(**role))
    await session.flush()

    # Optionally seed question templates for tests that need them
    if include_questions:
        for question in QUESTION_TEMPLATES:
            session.add(QuestionTemplate(**question))
        await session.flush()

    await session.commit()


@pytest.fixture()
async def async_client(test_client: TestClient) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for testing async routes."""
    transport = ASGITransport(app=app)  # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture()
async def async_client_with_questions(
    test_client_with_questions: TestClient,
) -> AsyncIterator[AsyncClient]:
    """Async HTTP client with seeded question templates."""
    transport = ASGITransport(app=app)  # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture()
async def db(test_client: TestClient) -> AsyncIterator[AsyncSession]:
    """Provide a database session for tests that need direct DB access."""
    session_factory = test_client.session_factory  # type: ignore
    async with session_factory() as session:
        yield session


@pytest.fixture()
def admin_token() -> str:
    """Generate admin JWT token for testing."""
    return create_access_token("admin-user", roles=["admin"])


@pytest.fixture()
def student_token() -> str:
    """Generate student JWT token for testing."""
    return create_access_token("student-user", roles=["student"])
