import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.dependencies import get_current_user
from app.main import app
from app.api.v1.auth import get_auth_service
from app.services.auth_service import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
)


@pytest.fixture
def mock_auth_service():
    return AsyncMock()


@pytest.fixture
def client(mock_auth_service):
    """Мокируем сервис"""
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()  # убираем мок


# ---------- тесты регистрации -----------
async def test_register_success(client, mock_auth_service):
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "register_user@mail.ru"
    mock_user.first_name = "Игорь"
    mock_user.last_name = "Берегов"
    mock_user.middle_name = None
    mock_user.is_active = True
    mock_auth_service.register.return_value = mock_user

    response = await client.post(
        "/auth/register",
        json={
            "first_name": "Игорь",
            "last_name": "Берегов",
            "email": "register_user@mail.ru",
            "password": "register_userpass123",
            "password_confirm": "register_userpass123",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "register_user@mail.ru"


async def test_register_return_error_if_password_confirm_different(
    client, mock_auth_service
):
    response = await client.post(
        "/auth/register",
        json={
            "first_name": "Игорь",
            "last_name": "Берегов",
            "email": "register_user@mail.ru",
            "password": "register_userpass123",
            "password_confirm": "other_pass123",
        },
    )

    assert response.status_code == 422

    # убеждаемся что сервис не был вызван так как ошибка ловится на уровне схем Pydantic
    mock_auth_service.register.assert_not_called()


async def test_register_return_error_if_email_already_exists(client, mock_auth_service):
    mock_auth_service.register.side_effect = EmailAlreadyExistsError(
        "Такой Email уже занят"
    )

    response = await client.post(
        "/auth/register",
        json={
            "first_name": "Игорь",
            "last_name": "Берегов",
            "email": "exists@mail.ru",
            "password": "register_userpass123",
            "password_confirm": "register_userpass123",
        },
    )

    assert response.status_code == 409


# ----------- тесты логина ------------


async def test_login_success_returns_token(client, mock_auth_service):
    mock_auth_service.login.return_value = "valid.jwt.token"

    response = await client.post(
        "/auth/login",
        json={"email": "login@mail.ru", "password": "succes_login_pass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "valid.jwt.token"
    assert data["token_type"] == "bearer"


async def test_login_wrong_credentials_returns_401(client, mock_auth_service):
    mock_auth_service.login.side_effect = InvalidCredentialsError("Невереный пароль")

    response = await client.post(
        "/auth/login", json={"email": "login@mail.ru", "password": "wrong_pass123"}
    )

    assert response.status_code == 401


async def test_login_inactive_user_returns_401(client, mock_auth_service):
    mock_auth_service.login.side_effect = InactiveUserError("Аккаунт деактивирован")

    response = await client.post(
        "/auth/login",
        json={"email": "deleted@mail.ru", "password": "inactive_user_pass123"},
    )

    assert response.status_code == 401


# ----------- тесты обновления профиля -----------


@pytest.fixture
def client_with_user(mock_auth_service):
    """
    Отдельная фикстура для роутов которые требуют аутентификации.
    Подменяем get_current_user чтобы не нужен был реальный токен,
    и get_auth_service чтобы не идти в БД.
    """

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "user@mail.ru"
    mock_user.first_name = "Иван"
    mock_user.last_name = "Петров"
    mock_user.middle_name = None
    mock_user.is_active = True

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_update_profile_success(client_with_user, mock_auth_service):
    """
    PATCH /auth/me — роут не вызывает сервис, он использует UserRepository напрямую.
    """
    updated_user = MagicMock()
    updated_user.id = uuid.uuid4()
    updated_user.email = "user@mail.ru"
    updated_user.first_name = "Фёдор"
    updated_user.last_name = "Петров"
    updated_user.middle_name = None
    updated_user.is_active = True
    mock_auth_service.update_profile.return_value = updated_user

    response = await client_with_user.patch("/auth/me", json={"first_name": "Фёдор"})
    assert response.status_code == 200


async def test_update_profile_without_token_returns_401():
    """
    Без токена — 401. Никаких подмен, система сама отклоняет.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch("/auth/me", json={"first_name": "Фёдор"})
    assert response.status_code == 401


async def test_update_profile_empty_body_still_valid(
    client_with_user, mock_auth_service
):
    """
    Граничный случай — пустое тело запроса.
    Все поля в UserUpdateRequest опциональны, поэтому 200.
    """
    unchanged_user = MagicMock()
    unchanged_user.id = uuid.uuid4()
    unchanged_user.email = "user@mail.ru"
    unchanged_user.first_name = "Иван"
    unchanged_user.last_name = "Петров"
    unchanged_user.middle_name = None
    unchanged_user.is_active = True
    mock_auth_service.update_profile.return_value = unchanged_user

    response = await client_with_user.patch("/auth/me", json={})
    assert response.status_code == 200


# ----------- тесты мягкого удаления -----------


async def test_delete_me_success(client_with_user, mock_auth_service):
    """
    DELETE /auth/me —  204
    """
    response = await client_with_user.delete("/auth/me")

    assert response.status_code == 204
    # убеждаемся что logout и soft_delete были вызваны
    mock_auth_service.logout.assert_called_once()
    mock_auth_service.soft_delete.assert_called_once()


async def test_delete_me_without_token_returns_401():
    """
    Без токена — 401. До сервиса не доходим вообще.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/auth/me")
    assert response.status_code == 401
