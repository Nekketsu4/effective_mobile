from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport
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
    mock_user.id = "some-uuid"
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
