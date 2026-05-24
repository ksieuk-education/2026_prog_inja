"""Тесты репозитория пользователей через Dishka + UoW."""

from uuid import uuid4

import pytest

from lib.app.domain.entities import User
from lib.infra.common.errors import SaveError


@pytest.mark.asyncio
async def test_create_and_get_by_login(uow) -> None:
    login = f"ivan_{uuid4().hex[:8]}"
    created = await uow.users.create(User(None, login, "Иван", "Петров"))
    assert created.id is not None
    found = await uow.users.get_by_login(login.upper())
    assert found is not None
    assert found.id == created.id
    assert found.login == login
    assert found.first_name == "Иван"


@pytest.mark.asyncio
async def test_search_by_name_mask(uow) -> None:
    token = uuid4().hex[:8]
    await uow.users.create(User(None, f"a{token}", "Иван", f"Сидоров{token}"))
    await uow.users.create(User(None, f"b{token}", "Пётр", f"Иванов{token}"))
    hits = await uow.users.search_by_name_mask(f"%Иван%{token}%")
    assert len(hits) == 2


@pytest.mark.asyncio
async def test_duplicate_login_raises_save_error(test_settings) -> None:
    from lib.app.common.uow import IUnitOfWork
    from lib.main.ioc.di import create_async_container

    login = f"dup_{uuid4().hex[:8]}"
    c1 = create_async_container(test_settings)
    try:
        async with c1() as request:
            w = await request.get(IUnitOfWork)
            await w.users.create(User(None, login, "А", "Б"))
    finally:
        await c1.close()

    c2 = create_async_container(test_settings)
    try:
        async with c2() as request:
            w = await request.get(IUnitOfWork)
            with pytest.raises(SaveError, match="пользователя"):
                await w.users.create(User(None, login, "В", "Г"))
    finally:
        await c2.close()
