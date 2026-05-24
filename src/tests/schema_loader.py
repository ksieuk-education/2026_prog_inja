"""Применение DDL из docker/postgres/initdb для тестовой БД."""

import pathlib
import re


def schema_sql_path() -> pathlib.Path:
    """Путь к init-скрипту схемы (тот же, что монтируется в PostgreSQL в Docker)."""
    return pathlib.Path(__file__).resolve().parents[2] / "docker" / "postgres" / "initdb" / "01-schema.sql"


def load_schema_statements() -> list[str]:
    """Разбивает SQL-файл на отдельные команды для asyncpg."""
    text = schema_sql_path().read_text(encoding="utf-8")
    without_comments = re.sub(r"--[^\n]*", "", text)
    return [part.strip() for part in without_comments.split(";") if part.strip()]
