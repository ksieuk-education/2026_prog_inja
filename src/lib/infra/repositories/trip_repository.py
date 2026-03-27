"""Репозиторий поездок (SQLite)."""

from datetime import UTC, datetime, timezone

import aiosqlite

from lib.app.common.repositories import ITripRepository
from lib.app.domain.entities import Trip, TripStatus


class TripRepository(ITripRepository):
    """Заказы поездок."""

    def __init__(self, conn: aiosqlite.Connection, display_tz: timezone) -> None:
        self._conn = conn
        self._display_tz = display_tz

    def _parse_created_at(self, value: str) -> datetime:
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value.removesuffix("Z")).replace(tzinfo=UTC)
        else:
            dt = datetime.fromisoformat(value)
            dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
        return dt.astimezone(self._display_tz)

    def _row_to_trip(self, row: aiosqlite.Row) -> Trip:
        return Trip(
            id=row["id"],
            user_id=row["user_id"],
            driver_id=row["driver_id"],
            status=TripStatus(row["status"]),
            created_at=self._parse_created_at(row["created_at"]),
        )

    async def create(self, trip: Trip) -> Trip:
        if trip.id is not None:
            msg = "при создании поездки поле id должно быть пустым"
            raise ValueError(msg)
        cur = await self._conn.execute(
            """
            INSERT INTO trips (user_id, driver_id, status)
            VALUES (?, ?, ?)
            """,
            (
                trip.user_id,
                trip.driver_id,
                trip.status.value,
            ),
        )
        new_id = cur.lastrowid
        await cur.close()
        if new_id is None:
            msg = "после вставки строки не получен идентификатор (lastrowid)"
            raise RuntimeError(msg)
        read = await self.get_by_id(int(new_id))
        if read is None:  # pragma: no cover
            msg = "не удалось прочитать созданную поездку из базы"
            raise RuntimeError(msg)
        return read

    async def get_by_id(self, trip_id: int) -> Trip | None:
        cur = await self._conn.execute(
            """
            SELECT id, user_id, driver_id, status, created_at
            FROM trips WHERE id = ?
            """,
            (trip_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if row is None:
            return None
        return self._row_to_trip(row)

    async def list_active(self) -> list[Trip]:
        cur = await self._conn.execute(
            """
            SELECT id, user_id, driver_id, status, created_at FROM trips
            WHERE status IN (?, ?)
            ORDER BY created_at DESC
            """,
            (TripStatus.PENDING.value, TripStatus.ACTIVE.value),
        )
        rows = await cur.fetchall()
        await cur.close()
        return [self._row_to_trip(r) for r in rows]

    async def list_history_for_user(self, user_id: int) -> list[Trip]:
        cur = await self._conn.execute(
            """
            SELECT id, user_id, driver_id, status, created_at FROM trips
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC
            """,
            (user_id, TripStatus.COMPLETED.value),
        )
        rows = await cur.fetchall()
        await cur.close()
        return [self._row_to_trip(r) for r in rows]

    async def try_accept(self, trip_id: int, driver_id: int) -> Trip | None:
        cur = await self._conn.execute(
            """
            UPDATE trips
            SET driver_id = ?, status = ?
            WHERE id = ? AND status = ?
            """,
            (
                driver_id,
                TripStatus.ACTIVE.value,
                trip_id,
                TripStatus.PENDING.value,
            ),
        )
        updated = cur.rowcount
        await cur.close()
        if updated != 1:
            return None
        return await self.get_by_id(trip_id)

    async def try_complete(self, trip_id: int) -> Trip | None:
        cur = await self._conn.execute(
            """
            UPDATE trips SET status = ?
            WHERE id = ? AND status = ?
            """,
            (TripStatus.COMPLETED.value, trip_id, TripStatus.ACTIVE.value),
        )
        updated = cur.rowcount
        await cur.close()
        if updated != 1:
            return None
        return await self.get_by_id(trip_id)
