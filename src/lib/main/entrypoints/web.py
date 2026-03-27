"""HTTP-приложение FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from lib.infra.common.sqlite_schema import ensure_sqlite_schema
from lib.main.ioc.di import create_async_container
from lib.main.settings import Settings
from lib.main.split_settings.api_settings import ApiSettings
from lib.present.api.routes.health_route import router_health
from lib.present.api.routes.taxi_route import router_taxi

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Собирает приложение: lifespan контейнера Dishka, OpenAPI из метаданных настроек.

    :param settings: явные настройки; иначе загружаются через ``Settings()``.
    """
    cfg = settings or Settings()
    container = create_async_container(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await ensure_sqlite_schema(cfg.database_settings.sqlite_path)
        yield
        await app.state.dishka_container.close()

    app = FastAPI(
        title=cfg.app_settings.title,
        version=cfg.app_settings.version,
        docs_url=f"{cfg.app_settings.prefix}/docs",
        redoc_url=f"{cfg.app_settings.prefix}/redoc",
        openapi_url=f"{cfg.app_settings.prefix}/openapi.json",
        lifespan=lifespan,
    )
    setup_dishka(container=container, app=app)
    app.include_router(router_health, prefix=cfg.app_settings.prefix)
    app.include_router(router_taxi, prefix=cfg.app_settings.prefix)
    return app


async def start_server(app: FastAPI, api_settings: ApiSettings) -> None:
    """Запускает ASGI-сервер uvicorn до остановки процесса."""
    try:
        config = uvicorn.Config(
            app=app,
            host=api_settings.host,
            port=api_settings.port,
        )
        server = uvicorn.Server(config)
        await server.serve()
    except BaseException:
        logger.exception("не удалось запустить FastAPI")
        raise
