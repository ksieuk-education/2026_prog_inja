"""Прямые тесты PostgreSQL-репозиториев (без Dishka)."""

from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from lib.app.domain.entities import Driver, Trip, TripStatus, User
from lib.infra.common.errors import SaveError
from lib.infra.repositories.driver_repository import DriverRepository
from lib.infra.repositories.trip_repository import TripRepository
from lib.infra.repositories.user_repository import UserRepository
from lib.main.settings import Settings


@pytest_asyncio.fixture
async def db_conn(test_settings: Settings) -> asyncpg.Connection:
    """Одно соединение, одна транзакция; в конце откат для изоляции следующих операций."""
    conn = await asyncpg.connect(test_settings.database_settings.build_dsn())
    transaction = conn.transaction()
    await transaction.start()
    try:
        yield conn
    finally:
        await transaction.rollback()
        await conn.close()


def _users(conn: asyncpg.Connection) -> UserRepository:
    return UserRepository(conn)


def _drivers(conn: asyncpg.Connection) -> DriverRepository:
    return DriverRepository(conn)


def _trips(conn: asyncpg.Connection, settings: Settings) -> TripRepository:
    return TripRepository(conn, settings.app_settings.get_timezone())


@pytest.mark.asyncio
async def test_user_repository_get_by_id_returns_none(db_conn: asyncpg.Connection) -> None:
    assert await _users(db_conn).get_by_id(999) is None


@pytest.mark.asyncio
async def test_user_repository_create_rejects_preset_id(db_conn: asyncpg.Connection) -> None:
    with pytest.raises(ValueError, match="id должно быть пустым"):
        await _users(db_conn).create(User(1, "a", "A", "B"))


@pytest.mark.asyncio
async def test_user_repository_search_wraps_plain_mask(db_conn: asyncpg.Connection) -> None:
    token = uuid4().hex[:8]
    repo = _users(db_conn)
    await repo.create(User(None, f"u1_{token}", "Мария", f"Иванова{token}"))
    hits = await repo.search_by_name_mask(f"Иванова{token}")
    assert len(hits) == 1
    assert hits[0].last_name == f"Иванова{token}"


@pytest.mark.asyncio
async def test_driver_repository_get_by_id_and_user(db_conn: asyncpg.Connection) -> None:
    urepo, drepo = _users(db_conn), _drivers(db_conn)
    user = await urepo.create(User(None, "du", "Д", "У"))
    assert user.id is not None
    dr = await drepo.create(Driver(None, user.id))
    by_id = await drepo.get_by_id(dr.id)
    by_uid = await drepo.get_by_user_id(user.id)
    assert by_id is not None and by_uid is not None
    assert by_id.id == by_uid.id == dr.id
    assert await drepo.get_by_id(99999) is None
    assert await drepo.get_by_user_id(99999) is None


@pytest.mark.asyncio
async def test_driver_repository_fk_violation(db_conn: asyncpg.Connection) -> None:
    with pytest.raises(SaveError, match="водителя"):
        await _drivers(db_conn).create(Driver(None, 999_999))


@pytest.mark.asyncio
async def test_driver_repository_duplicate_user(db_conn: asyncpg.Connection) -> None:
    urepo, drepo = _users(db_conn), _drivers(db_conn)
    u = await urepo.create(User(None, "one", "О", "Дин"))
    assert u.id is not None
    await drepo.create(Driver(None, u.id))
    with pytest.raises(SaveError, match="водителя"):
        await drepo.create(Driver(None, u.id))


@pytest.mark.asyncio
async def test_driver_repository_create_rejects_preset_id(db_conn: asyncpg.Connection) -> None:
    with pytest.raises(ValueError, match="id должно быть пустым"):
        await _drivers(db_conn).create(Driver(1, 1))


@pytest.mark.asyncio
async def test_trip_repository_get_missing(db_conn: asyncpg.Connection, test_settings: Settings) -> None:
    assert await _trips(db_conn, test_settings).get_by_id(999) is None


@pytest.mark.asyncio
async def test_trip_repository_create_rejects_preset_id(
    db_conn: asyncpg.Connection,
    test_settings: Settings,
) -> None:
    with pytest.raises(ValueError, match="id должно быть пустым"):
        await _trips(db_conn, test_settings).create(
            Trip(1, 1, None, TripStatus.PENDING),
        )


@pytest.mark.asyncio
async def test_trip_repository_accept_complete_idempotent(
    db_conn: asyncpg.Connection,
    test_settings: Settings,
) -> None:
    urepo, drepo, trepo = _users(db_conn), _drivers(db_conn), _trips(db_conn, test_settings)
    client = await urepo.create(User(None, "c", "К", "Л"))
    duser = await urepo.create(User(None, "dv", "В", "О"))
    assert client.id is not None and duser.id is not None
    driver = await drepo.create(Driver(None, duser.id))
    trip = await trepo.create(Trip(None, client.id, None, TripStatus.PENDING))
    assert trip.id is not None

    ok1 = await trepo.try_accept(trip.id, driver.id)
    assert ok1 is not None and ok1.status == TripStatus.ACTIVE
    ok2 = await trepo.try_accept(trip.id, driver.id)
    assert ok2 is None

    done = await trepo.try_complete(trip.id)
    assert done is not None and done.status == TripStatus.COMPLETED
    assert await trepo.try_complete(trip.id) is None


@pytest.mark.asyncio
async def test_trip_repository_complete_fails_on_pending(
    db_conn: asyncpg.Connection,
    test_settings: Settings,
) -> None:
    urepo, trepo = _users(db_conn), _trips(db_conn, test_settings)
    u = await urepo.create(User(None, "p", "П", "Е"))
    assert u.id is not None
    trip = await trepo.create(Trip(None, u.id, None, TripStatus.PENDING))
    assert trip.id is not None
    assert await trepo.try_complete(trip.id) is None


@pytest.mark.asyncio
async def test_trip_repository_list_history_only_completed(
    db_conn: asyncpg.Connection,
    test_settings: Settings,
) -> None:
    urepo, drepo, trepo = _users(db_conn), _drivers(db_conn), _trips(db_conn, test_settings)
    u = await urepo.create(User(None, "h", "Х", "И"))
    assert u.id is not None
    await trepo.create(Trip(None, u.id, None, TripStatus.PENDING))
    assert await trepo.list_history_for_user(u.id) == []

    duser = await urepo.create(User(None, "dh", "Д", "Х"))
    assert duser.id is not None
    dr = await drepo.create(Driver(None, duser.id))
    t2 = await trepo.create(Trip(None, u.id, None, TripStatus.PENDING))
    await trepo.try_accept(t2.id, dr.id)
    await trepo.try_complete(t2.id)
    hist = await trepo.list_history_for_user(u.id)
    assert len(hist) == 1
    assert hist[0].status == TripStatus.COMPLETED


@pytest.mark.asyncio
async def test_trip_repository_active_lists_pending_and_active(
    db_conn: asyncpg.Connection,
    test_settings: Settings,
) -> None:
    urepo, drepo, trepo = _users(db_conn), _drivers(db_conn), _trips(db_conn, test_settings)
    u = await urepo.create(User(None, "act", "А", "К"))
    assert u.id is not None
    await trepo.create(Trip(None, u.id, None, TripStatus.PENDING))
    du = await urepo.create(User(None, "actd", "Д", "К"))
    dr = await drepo.create(Driver(None, du.id))
    t2 = await trepo.create(Trip(None, u.id, None, TripStatus.PENDING))
    await trepo.try_accept(t2.id, dr.id)
    active = await trepo.list_active()
    statuses = {t.status for t in active}
    assert TripStatus.PENDING in statuses and TripStatus.ACTIVE in statuses
