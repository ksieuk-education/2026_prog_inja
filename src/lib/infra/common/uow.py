"""
Реализация UoW для SQLite (aiosqlite).
"""

import logging
from datetime import timezone
from types import TracebackType
from typing import Self

import aiosqlite

from lib.app.common.repositories import IDriverRepository, ITripRepository, IUserRepository
from lib.app.common.uow import IUnitOfWork
from lib.infra.repositories.driver_repository import DriverRepository
from lib.infra.repositories.trip_repository import TripRepository
from lib.infra.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class SQLiteUnitOfWork(IUnitOfWork):
    """Транзакция: одно соединение и три репозитория."""

    def __init__(self, conn: aiosqlite.Connection, display_tz: timezone) -> None:
        self._conn = conn
        self._users = UserRepository(conn)
        self._drivers = DriverRepository(conn)
        self._trips = TripRepository(conn, display_tz)

    @property
    def users(self) -> IUserRepository:
        return self._users

    @property
    def drivers(self) -> IDriverRepository:
        return self._drivers

    @property
    def trips(self) -> ITripRepository:
        return self._trips

    async def __aenter__(self) -> Self:
        await self._conn.execute("BEGIN")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                logger.debug("UoW rollback из-за исключения: %s", exc_val)
                await self._conn.rollback()
            else:
                await self._conn.commit()
        except aiosqlite.Error:
            logger.exception("Ошибка SQLite при завершении UoW, откат.")
            await self._conn.rollback()
            raise

    async def commit(self) -> None:
        await self._conn.commit()
        await self._conn.execute("BEGIN")

    async def rollback(self) -> None:
        await self._conn.rollback()
        await self._conn.execute("BEGIN")
