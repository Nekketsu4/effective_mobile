import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies import get_current_user
from app.models.role import RoleName
from app.services.user_management_service import (
    UserNotFoundError,
    RoleNotFoundError,
    CannotModifyAdminError,
    CannotDeleteSelfError,
)
from app.api.v1.admin import get_user_management_service


def make_admin():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "admin@test.com"
    user.is_active = True
    user.role = MagicMock()
    user.role.name = RoleName.ADMIN
    user.role_id = uuid.uuid4()
    return user


def make_regular_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@test.com"
    user.is_active = True
    user.role = MagicMock()
    user.role.name = RoleName.USER
    user.role_id = uuid.uuid4()
    return user


@pytest.fixture
def mock_user_management_service():
    return AsyncMock()


@pytest.fixture
async def admin_client(mock_user_management_service):
    app.dependency_overrides[get_current_user] = lambda: make_admin()
    app.dependency_overrides[get_user_management_service] = lambda: (
        mock_user_management_service
    )
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
async def regular_client():
    app.dependency_overrides[get_current_user] = lambda: make_regular_user()
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
async def anonymous_client():
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ----------- защита роутов -----------


async def test_get_users_anonymous_returns_401(anonymous_client):
    response = await anonymous_client.get("/admin/users")
    assert response.status_code == 401


async def test_get_users_regular_user_returns_403(regular_client):
    response = await regular_client.get("/admin/users")
    assert response.status_code == 403


# ----------- GET /admin/users -----------


async def test_get_all_users_returns_200(admin_client, mock_user_management_service):
    """
    Список пользователей — проверяем статус и что сервис был вызван.
    from_user вызывается в роуте, поэтому настраиваем мок с нужными атрибутами.
    """
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "test@test.com"
    mock_user.first_name = "Иван"
    mock_user.last_name = "Петров"
    mock_user.middle_name = None
    mock_user.is_active = True
    mock_user.role_id = uuid.uuid4()
    mock_user.role = MagicMock()
    mock_user.role.name = RoleName.USER
    mock_user_management_service.get_all_users.return_value = [mock_user]

    response = await admin_client.get("/admin/users")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    mock_user_management_service.get_all_users.assert_called_once()


# ----------- GET /admin/users/{user_id} -----------


async def test_get_user_by_id_returns_200(admin_client, mock_user_management_service):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.email = "test@test.com"
    mock_user.first_name = "Иван"
    mock_user.last_name = "Петров"
    mock_user.middle_name = None
    mock_user.is_active = True
    mock_user.role_id = uuid.uuid4()
    mock_user.role = MagicMock()
    mock_user.role.name = RoleName.USER
    mock_user_management_service.get_user_by_id.return_value = mock_user

    response = await admin_client.get(f"/admin/users/{user_id}")

    assert response.status_code == 200
    mock_user_management_service.get_user_by_id.assert_called_once_with(user_id)


async def test_get_user_by_id_not_found_returns_404(
    admin_client, mock_user_management_service
):
    mock_user_management_service.get_user_by_id.side_effect = UserNotFoundError()
    response = await admin_client.get(f"/admin/users/{uuid.uuid4()}")
    assert response.status_code == 404


# ----------- PATCH /admin/users/{user_id}/role -----------


async def test_assign_role_success_returns_200(
    admin_client, mock_user_management_service
):
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.email = "test@test.com"
    mock_user.first_name = "Иван"
    mock_user.last_name = "Петров"
    mock_user.middle_name = None
    mock_user.is_active = True
    mock_user.role_id = uuid.uuid4()
    mock_user.role = MagicMock()
    mock_user.role.name = RoleName.MANAGER
    mock_user_management_service.assign_role.return_value = mock_user

    response = await admin_client.patch(
        f"/admin/users/{user_id}/role", json={"role_id": str(uuid.uuid4())}
    )
    assert response.status_code == 200


async def test_assign_role_to_admin_returns_403(
    admin_client, mock_user_management_service
):
    mock_user_management_service.assign_role.side_effect = CannotModifyAdminError()
    response = await admin_client.patch(
        f"/admin/users/{uuid.uuid4()}/role", json={"role_id": str(uuid.uuid4())}
    )
    assert response.status_code == 403


async def test_assign_nonexistent_role_returns_404(
    admin_client, mock_user_management_service
):
    mock_user_management_service.assign_role.side_effect = RoleNotFoundError()
    response = await admin_client.patch(
        f"/admin/users/{uuid.uuid4()}/role", json={"role_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404


# ----------- DELETE /admin/users/{user_id} -----------


async def test_delete_user_returns_204(admin_client, mock_user_management_service):
    response = await admin_client.delete(f"/admin/users/{uuid.uuid4()}")
    assert response.status_code == 204
    assert response.content == b""


async def test_delete_self_returns_400(admin_client, mock_user_management_service):
    mock_user_management_service.delete_user.side_effect = CannotDeleteSelfError()
    response = await admin_client.delete(f"/admin/users/{uuid.uuid4()}")
    assert response.status_code == 400


async def test_delete_admin_returns_403(admin_client, mock_user_management_service):
    mock_user_management_service.delete_user.side_effect = CannotModifyAdminError()
    response = await admin_client.delete(f"/admin/users/{uuid.uuid4()}")
    assert response.status_code == 403


async def test_delete_nonexistent_user_returns_404(
    admin_client, mock_user_management_service
):
    mock_user_management_service.delete_user.side_effect = UserNotFoundError()
    response = await admin_client.delete(f"/admin/users/{uuid.uuid4()}")
    assert response.status_code == 404
