"""Тесты InMemoryKVStore (без Dishka)."""

import pytest

from lib.infra.adapters.in_memory_kv import TTL_KEY_MISSING, TTL_NO_EXPIRE, InMemoryKVStore


@pytest.mark.asyncio
async def test_set_get_delete() -> None:
    store = InMemoryKVStore()
    assert await store.get("k") is None
    await store.set("k", "v")
    assert await store.get("k") == "v"
    assert await store.delete("k") == 1
    assert await store.get("k") is None


@pytest.mark.asyncio
async def test_ttl_expire_and_incr() -> None:
    store = InMemoryKVStore()
    await store.set("n", "0")
    assert await store.incr("n") == 1
    assert await store.get("n") == "1"
    assert await store.ttl("missing") == TTL_KEY_MISSING
    await store.set("noex", "1")
    assert await store.ttl("noex") == TTL_NO_EXPIRE
    await store.set("e", "x", ex=3600)
    assert await store.ttl("e") > 0
    assert await store.expire("e", 7200) is True
    with pytest.raises(ValueError, match="положительным"):
        await store.set("bad", "v", ex=0)
