"""Общие фикстуры: БД, Dishka, UoW."""

from collections.abc import AsyncGenerator

import pytest_asyncio

from lib.app.common.uow import IUnitOfWork
from lib.infra.common.sqlite_schema import ensure_sqlite_schema
from lib.main.ioc.di import create_async_container
from lib.main.settings import Settings
from lib.main.split_settings.database_settings import DatabaseSettings
from lib.main.split_settings.logging_settings import LoggingSettings


@pytest_asyncio.fixture
async def test_settings(tmp_path) -> Settings:
    """Настройки с временным файлом SQLite и логами в tmp."""
    db_path = tmp_path / "test.sqlite3"
    path_str = str(db_path)
    await ensure_sqlite_schema(path_str)
    return Settings(
        use_config_yml=False,
        database_settings=DatabaseSettings(sqlite_path=path_str),
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
