"""Инициализация схемы SQLite."""

import pathlib

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL COLLATE NOCASE UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    driver_id INTEGER REFERENCES drivers(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_trips_user ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_created ON trips(created_at);
"""


async def ensure_sqlite_schema(sqlite_path: str) -> None:
    """
    Создаёт родительские каталоги и таблицы при необходимости.

    :param sqlite_path: путь к файлу БД
    """
    path = pathlib.Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(sqlite_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
