"""Тесты репозитория пользователей через Dishka + UoW."""

import pytest

from lib.app.domain.entities import User
from lib.infra.common.errors import SaveError


@pytest.mark.asyncio
async def test_create_and_get_by_login(uow) -> None:
    created = await uow.users.create(User(None, "ivan", "Иван", "Петров"))
    assert created.id == 1
    found = await uow.users.get_by_login("IVAN")
    assert found is not None
    assert found.login == "ivan"
    assert found.first_name == "Иван"


@pytest.mark.asyncio
async def test_search_by_name_mask(uow) -> None:
    await uow.users.create(User(None, "a", "Иван", "Сидоров"))
    await uow.users.create(User(None, "b", "Пётр", "Иванов"))
    hits = await uow.users.search_by_name_mask("%Иван%")
    assert len(hits) == 2


@pytest.mark.asyncio
async def test_duplicate_login_raises_save_error(test_settings) -> None:
    from lib.app.common.uow import IUnitOfWork
    from lib.main.ioc.di import create_async_container

    c1 = create_async_container(test_settings)
    try:
        async with c1() as request:
            w = await request.get(IUnitOfWork)
            await w.users.create(User(None, "dup", "А", "Б"))
    finally:
        await c1.close()

    c2 = create_async_container(test_settings)
    try:
        async with c2() as request:
            w = await request.get(IUnitOfWork)
            with pytest.raises(SaveError, match="пользователя"):
                await w.users.create(User(None, "dup", "В", "Г"))
    finally:
        await c2.close()
