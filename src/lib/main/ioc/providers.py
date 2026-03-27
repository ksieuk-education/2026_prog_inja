"""Провайдеры Dishka: приложение и инфраструктура."""

from collections.abc import AsyncIterator

import aiosqlite
from dishka import Provider, Scope, from_context, provide  # pyright: ignore[reportUnknownVariableType]

from lib.app.common.uow import IUnitOfWork
from lib.infra.common.uow import SQLiteUnitOfWork
from lib.main.settings import Settings


class InfraProvider(Provider):
    """Соединение REQUEST-scoped и транзакция UoW."""

    @provide(scope=Scope.REQUEST)
    async def sqlite_connection(self, settings: Settings) -> AsyncIterator[aiosqlite.Connection]:
        path = settings.database_settings.sqlite_path
        conn = await aiosqlite.connect(path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            await conn.close()

    @provide(scope=Scope.REQUEST)
    async def unit_of_work(self, conn: aiosqlite.Connection, settings: Settings) -> AsyncIterator[IUnitOfWork]:
        display_tz = settings.app_settings.get_timezone()
        async with SQLiteUnitOfWork(conn, display_tz) as uow:
            yield uow


class AppProvider(Provider):
    """Базовые зависимости приложения (APP scope)."""

    settings = from_context(provides=Settings, scope=Scope.APP)
