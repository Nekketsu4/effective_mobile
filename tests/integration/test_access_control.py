from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_current_user, require_permission
from app.models.business_element import BusinessElementName
from app.models.role import RoleName


def make_user(role: RoleName) -> MagicMock:
    """Создаем мок пользователя с нужной ролью"""
    mock_user = MagicMock()
    mock_user.id = "some-user-uuid"
    mock_user.email = f"{role.value}@mail.ru"
    mock_user.is_active = True
    mock_user.role = MagicMock()
    mock_user.role.name = role
    mock_user.role_id = "some-role-uuid"
    return mock_user


@pytest.fixture
async def client_as_user():
    """
    Клиент от имени обычного пользователя
    Подменим get_current_user чтобы не запрашивать реальный токен
    """
    app.dependency_overrides[get_current_user] = lambda: make_user(role=RoleName.USER)
    # мокаю require_permission чтобы не бегал в БД за uuid
    app.dependency_overrides[
        require_permission(BusinessElementName.PRODUCTS, "read")
    ] = lambda: None  # просто пропускаем проверку прав
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """Клиент без токена"""
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_products_return_401_if_user_without_token(client_no_auth):
    """Проверяем что вернет 401 ошибку"""
    response = await client_no_auth.get("/mock/products")
    assert response.status_code == 401


async def test_products_return_200_if_user_token_is_valid(client_as_user):
    response = await client_as_user.get("/mock/products")
    # если у роли user есть привелегия can_read для endpoint'а products
    # то вернет 200
    assert response.status_code == 200


async def test_products_without_permission_returns_403():
    """
    Пользователь аутентифицирован, но у его роли нет прав на products.
    """

    def mock_no_permission():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на действие read для products",
        )

    app.dependency_overrides[get_current_user] = lambda: make_user(RoleName.GUEST)
    app.dependency_overrides[
        require_permission(BusinessElementName.PRODUCTS, "read")
    ] = mock_no_permission

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/mock/products")

    app.dependency_overrides.clear()
    assert response.status_code == 403
