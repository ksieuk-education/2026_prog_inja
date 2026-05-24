"""Тесты аутентификации: сервис, middleware и HTTP API."""

import pytest
from fastapi.testclient import TestClient

from lib.application.auth.errors import AuthenticationError
from lib.application.auth.jwt_token_service import JwtTokenService
from lib.application.auth.password_hasher import PasswordHasher
from lib.main.entrypoints.web import create_app
from lib.main.settings import Settings
from lib.main.split_settings.auth_settings import AuthSettings
from lib.present.api.middleware.auth_middleware import is_protected_route


@pytest.fixture
def auth_settings() -> AuthSettings:
    return AuthSettings(jwt_secret="test-secret-key-at-least-32-bytes-long!!")


def test_password_hasher_roundtrip() -> None:
    hasher = PasswordHasher()
    stored = hasher.hash("secret123")
    assert hasher.verify("secret123", stored)
    assert not hasher.verify("wrong", stored)


def test_jwt_token_service_decode(auth_settings: AuthSettings) -> None:
    service = JwtTokenService(auth_settings)
    token = service.create_access_token(user_id=42, login="alice")
    payload = service.decode_access_token(token)
    assert payload["user_id"] == 42
    assert payload["login"] == "alice"


def test_jwt_invalid_token_raises(auth_settings: AuthSettings) -> None:
    service = JwtTokenService(auth_settings)
    with pytest.raises(AuthenticationError):
        service.decode_access_token("not-a-valid-token")


def test_is_protected_route() -> None:
    assert is_protected_route(method="POST", path_without_prefix="/drivers")
    assert is_protected_route(method="POST", path_without_prefix="/trips")
    assert is_protected_route(method="GET", path_without_prefix="/users/5/trips/history")
    assert not is_protected_route(method="GET", path_without_prefix="/trips/active")
    assert not is_protected_route(method="POST", path_without_prefix="/users")


@pytest.fixture
def api_client(test_settings: Settings) -> TestClient:
    settings = test_settings.model_copy(
        update={
            "auth_settings": AuthSettings(jwt_secret="test-secret-key-at-least-32-bytes-long!!"),
        },
    )
    return TestClient(create_app(settings))


def test_register_login_and_access_protected(api_client: TestClient) -> None:
    from uuid import uuid4

    login = f"auth_user_{uuid4().hex[:8]}"
    reg = api_client.post(
        "/api/taxi/v1/auth/register",
        json={
            "login": login,
            "password": "password1",
            "first_name": "Auth",
            "last_name": "User",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    login_resp = api_client.post(
        "/api/taxi/v1/auth/login",
        json={"login": login, "password": "password1"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["access_token"]

    user_id = reg.json()["user"]["id"]
    no_auth = api_client.post(
        "/api/taxi/v1/trips",
        json={"user_id": user_id},
    )
    assert no_auth.status_code == 401

    with_auth = api_client.post(
        "/api/taxi/v1/trips",
        json={"user_id": user_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert with_auth.status_code == 201


def test_protected_driver_register_requires_auth(api_client: TestClient) -> None:
    from uuid import uuid4

    login = f"driver_user_{uuid4().hex[:8]}"
    reg = api_client.post(
        "/api/taxi/v1/auth/register",
        json={
            "login": login,
            "password": "password1",
            "first_name": "D",
            "last_name": "U",
        },
    )
    user_id = reg.json()["user"]["id"]
    token = reg.json()["access_token"]

    denied = api_client.post("/api/taxi/v1/drivers", json={"user_id": user_id})
    assert denied.status_code == 401

    ok = api_client.post(
        "/api/taxi/v1/drivers",
        json={"user_id": user_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 201


@pytest.mark.asyncio
async def test_auth_service_login_wrong_password(uow, auth_settings: AuthSettings) -> None:
    from uuid import uuid4

    from lib.application.auth.auth_service import AuthService

    login = f"svc_{uuid4().hex[:8]}"
    hasher = PasswordHasher()
    jwt_service = JwtTokenService(auth_settings)
    service = AuthService(uow, hasher, jwt_service)
    await service.register(
        login=login,
        password="correct",
        first_name="A",
        last_name="B",
    )
    with pytest.raises(AuthenticationError, match="неверный"):
        await service.login(login=login, password="wrong")
