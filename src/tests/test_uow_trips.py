"""Сценарии поездок: Dishka + PostgreSQL UoW."""

from uuid import uuid4

import pytest

from lib.app.common.uow import IUnitOfWork
from lib.app.domain.entities import Driver, Trip, TripStatus, User
from lib.main.ioc.di import create_async_container
from lib.main.settings import Settings


@pytest.mark.asyncio
async def test_trip_accept_and_complete(test_settings: Settings) -> None:
    uid_client: int
    driver_pk: int
    suffix = uuid4().hex[:8]

    c_setup = create_async_container(test_settings)
    try:
        async with c_setup() as request:
            uow = await request.get(IUnitOfWork)
            client = await uow.users.create(User(None, f"client1_{suffix}", "Клиент", "Один"))
            driver_user = await uow.users.create(User(None, f"driver1_{suffix}", "Водитель", "Раз"))
            assert client.id is not None
            assert driver_user.id is not None
            driver_row = await uow.drivers.create(Driver(None, driver_user.id))
            assert driver_row.id is not None
            uid_client = client.id
            driver_pk = driver_row.id
    finally:
        await c_setup.close()

    trip_id: int
    c_trip = create_async_container(test_settings)
    try:
        async with c_trip() as request:
            uow = await request.get(IUnitOfWork)
            trip = await uow.trips.create(Trip(None, uid_client, None, TripStatus.PENDING))
            assert trip.id is not None
            assert trip.status == TripStatus.PENDING
            trip_id = trip.id
    finally:
        await c_trip.close()

    c_accept = create_async_container(test_settings)
    try:
        async with c_accept() as request:
            uow = await request.get(IUnitOfWork)
            accepted = await uow.trips.try_accept(trip_id, driver_pk)
            assert accepted is not None
            assert accepted.status == TripStatus.ACTIVE
            assert accepted.driver_id == driver_pk
    finally:
        await c_accept.close()

    c_done = create_async_container(test_settings)
    try:
        async with c_done() as request:
            uow = await request.get(IUnitOfWork)
            completed = await uow.trips.try_complete(trip_id)
            assert completed is not None
            assert completed.status == TripStatus.COMPLETED
    finally:
        await c_done.close()

    c_hist = create_async_container(test_settings)
    try:
        async with c_hist() as request:
            uow = await request.get(IUnitOfWork)
            history = await uow.trips.list_history_for_user(uid_client)
            assert any(t.id == trip_id for t in history)
            trip_in_history = next(t for t in history if t.id == trip_id)
            assert trip_in_history.created_at is not None
            assert trip_in_history.created_at.tzinfo == test_settings.app_settings.get_timezone()
    finally:
        await c_hist.close()


@pytest.mark.asyncio
async def test_list_active_pending(uow: IUnitOfWork) -> None:
    suffix = uuid4().hex[:8]
    u1 = await uow.users.create(User(None, f"p1_{suffix}", "А", "Б"))
    assert u1.id is not None
    before = await uow.trips.list_active()
    created = await uow.trips.create(Trip(None, u1.id, None, TripStatus.PENDING))
    active = await uow.trips.list_active()
    assert len(active) == len(before) + 1
    assert any(t.id == created.id and t.status == TripStatus.PENDING for t in active)
