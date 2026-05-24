"""Общие фикстуры: БД, Dishka, UoW."""

import asyncio
import os
from collections.abc import AsyncGenerator, Iterator
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from lib.app.common.uow import IUnitOfWork
from lib.main.ioc.di import create_async_container
from lib.main.settings import Settings
from lib.main.split_settings.auth_settings import AuthSettings
from lib.main.split_settings.database_settings import DatabaseSettings
from lib.main.split_settings.logging_settings import LoggingSettings
from tests.schema_loader import load_schema_statements


async def _apply_schema(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        for statement in load_schema_statements():
            await conn.execute(statement)
    finally:
        await conn.close()


def _normalize_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg2://", "postgresql://")


@pytest.fixture(scope="session")
def postgres_dsn() -> Iterator[str]:
    """
    DSN PostgreSQL для тестов.

    Приоритет: переменная ``TEST_DATABASE_DSN``, иначе контейнер testcontainers.
    """
    external = os.environ.get("TEST_DATABASE_DSN")
    if external:
        dsn = _normalize_dsn(external)
        asyncio.run(_apply_schema(dsn))
        yield dsn
        return

    try:
        with PostgresContainer(
            image="postgres:16-alpine",
            username="user",
            password="taxipass",
            dbname="taxidb",
        ) as postgres:
            dsn = _normalize_dsn(postgres.get_connection_url())
            asyncio.run(_apply_schema(dsn))
            yield dsn
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL для тестов недоступен (Docker/testcontainers): {exc}")


@pytest_asyncio.fixture
async def test_settings(postgres_dsn: str, tmp_path) -> Settings:
    """Настройки с PostgreSQL и логами в tmp."""
    parsed = urlparse(postgres_dsn)
    return Settings(
        use_config_yml=False,
        auth_settings=AuthSettings(jwt_secret="test-secret-key-at-least-32-bytes-long!!"),
        database_settings=DatabaseSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=(parsed.path or "/taxidb").removeprefix("/"),
            user=parsed.username or "user",
            password=parsed.password or "taxipass",
        ),
        logging_settings=LoggingSettings(
            log_dir=str(tmp_path / "logs"),
            log_default_handlers=("console",),
        ),
    )


@pytest_asyncio.fixture
async def uow(test_settings: Settings) -> AsyncGenerator[IUnitOfWork]:
    """Один HTTP-request scope Dishka: соединение, транзакция UoW и commit при выходе."""
    container = create_async_container(test_settings)
    try:
        async with container() as request:
            uow_instance = await request.get(IUnitOfWork)
            yield uow_instance
    finally:
        await container.close()
