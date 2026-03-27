"""Репозиторий пользователей (SQLite)."""

import sqlite3

import aiosqlite

from lib.app.common.repositories import IUserRepository
from lib.app.domain.entities import User
from lib.infra.common.errors import SaveError


class UserRepository(IUserRepository):
    """CRUD пользователей в одной SQLite-транзакции."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def create(self, user: User) -> User:
        if user.id is not None:
            msg = "при создании пользователя поле id должно быть пустым"
            raise ValueError(msg)
        try:
            cur = await self._conn.execute(
                """
                INSERT INTO users (login, first_name, last_name)
                VALUES (?, ?, ?)
                """,
                (user.login, user.first_name, user.last_name),
            )
        except sqlite3.IntegrityError as exc:
            raise SaveError("ошибка сохранения пользователя: дубликат или нарушение ограничений БД") from exc
        new_id = cur.lastrowid
        await cur.close()
        if new_id is None:
            msg = "после вставки строки не получен идентификатор (lastrowid)"
            raise RuntimeError(msg)
        return User(
            id=int(new_id),
            login=user.login,
            first_name=user.first_name,
            last_name=user.last_name,
        )

    async def get_by_id(self, user_id: int) -> User | None:
        cur = await self._conn.execute(
            "SELECT id, login, first_name, last_name FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if row is None:
            return None
        return User(id=row["id"], login=row["login"], first_name=row["first_name"], last_name=row["last_name"])

    async def get_by_login(self, login: str) -> User | None:
        cur = await self._conn.execute(
            "SELECT id, login, first_name, last_name FROM users WHERE login = ? COLLATE NOCASE",
            (login,),
        )
        row = await cur.fetchone()
        await cur.close()
        if row is None:
            return None
        return User(id=row["id"], login=row["login"], first_name=row["first_name"], last_name=row["last_name"])

    async def search_by_name_mask(self, pattern: str) -> list[User]:
        like = pattern if "%" in pattern or "_" in pattern else f"%{pattern}%"
        cur = await self._conn.execute(
            """
            SELECT id, login, first_name, last_name FROM users
            WHERE (first_name || ' ' || last_name) LIKE ? COLLATE NOCASE
            ORDER BY last_name, first_name
            """,
            (like,),
        )
        rows = await cur.fetchall()
        await cur.close()
        return [
            User(id=r["id"], login=r["login"], first_name=r["first_name"], last_name=r["last_name"]) for r in rows
        ]
