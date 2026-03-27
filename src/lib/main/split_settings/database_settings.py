"""Настройки базы данных."""

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """Параметры SQLite."""

    sqlite_path: str = Field(
        default="data/app.db",
        description="Путь к файлу SQLite (относительно рабочего каталога процесса).",
    )
