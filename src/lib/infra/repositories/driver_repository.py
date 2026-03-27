"""Репозиторий водителей (SQLite)."""

import sqlite3

import aiosqlite

from lib.app.common.repositories import IDriverRepository
from lib.app.domain.entities import Driver
from lib.infra.common.errors import SaveError


class DriverRepository(IDriverRepository):
    """Регистрация и чтение водителей."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def create(self, driver: Driver) -> Driver:
        if driver.id is not None:
            msg = "при создании водителя поле id должно быть пустым"
            raise ValueError(msg)
        try:
            cur = await self._conn.execute(
                "INSERT INTO drivers (user_id) VALUES (?)",
                (driver.user_id,),
            )
        except sqlite3.IntegrityError as exc:
            raise SaveError("ошибка сохранения водителя: дубликат или нарушение ограничений БД") from exc
        new_id = cur.lastrowid
        await cur.close()
        if new_id is None:
            msg = "после вставки строки не получен идентификатор (lastrowid)"
            raise RuntimeError(msg)
        return Driver(id=int(new_id), user_id=driver.user_id)

    async def get_by_id(self, driver_id: int) -> Driver | None:
        cur = await self._conn.execute(
            "SELECT id, user_id FROM drivers WHERE id = ?",
            (driver_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if row is None:
            return None
        return Driver(id=row["id"], user_id=row["user_id"])

    async def get_by_user_id(self, user_id: int) -> Driver | None:
        cur = await self._conn.execute(
            "SELECT id, user_id FROM drivers WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if row is None:
            return None
        return Driver(id=row["id"], user_id=row["user_id"])
