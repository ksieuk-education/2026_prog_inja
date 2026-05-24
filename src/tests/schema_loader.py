"""Применение DDL из schema.sql для тестовой БД."""

import pathlib
import re


def schema_sql_path() -> pathlib.Path:
    """Путь к schema.sql в корне репозитория."""
    return pathlib.Path(__file__).resolve().parents[2] / "schema.sql"


def load_schema_statements() -> list[str]:
    """Разбивает SQL-файл на отдельные команды для asyncpg."""
    text = schema_sql_path().read_text(encoding="utf-8")
    without_comments = re.sub(r"--[^\n]*", "", text)
    return [part.strip() for part in without_comments.split(";") if part.strip()]
