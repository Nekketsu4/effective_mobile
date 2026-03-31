import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies import get_current_user
from app.api.v1.admin import get_access_service

from app.models.business_element import BusinessElementName
from app.models.role import RoleName
from app.services.access_service import (
    CannotModifyAdminError,
    RuleAlreadyExistsError,
    RuleNotFoundError,
)


def make_admin():
    """Создаем мок админа"""
    admin_user = MagicMock()
    admin_user.id = uuid.uuid4()
    admin_user.email = "admin@mail.ru"
    admin_user.is_active = True
    admin_user.role = MagicMock()
    admin_user.role.name = RoleName.ADMIN
    return admin_user


def make_user():
    """Создаем обычного пользователя"""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@mail.ru"
    user.is_active = True
    user.role = MagicMock()
    user.role.name = RoleName.USER
    return user


@pytest.fixture
def mock_access_service():
    return AsyncMock()


@pytest.fixture
async def admin_client(mock_access_service):
    """
    Клиент от имени админа
    Делаем подмену get_access_service и get_current_user
    чтобы запросы не летели в БД в тестах
    """
    app.dependency_overrides[get_current_user] = lambda: make_admin()
    app.dependency_overrides[get_access_service] = lambda: mock_access_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
async def user_client():
    """
    Клиент от имени пользователя
    Делаем подмену get_current_user
    чтобы запросы не летели в БД в тестах
    """
    app.dependency_overrides[get_current_user] = lambda: make_user()
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
async def guest_client():
    """
    Не аутентифицированный клиент(гость)
    ничего не мокаем, ожидаем 401 ошибку
    """
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# --------- тесты защиты роутов ----------
# проверяем корректную работы защиты роутов


async def test_get_roles_return_401_if_guest(guest_client):
    """Нет токена - 401"""
    response = await guest_client.get("/admin/roles")
    assert response.status_code == 401


async def test_get_roles_return_403_if_user(user_client):
    """
    Есть токен, но нет прав админа - 403
    """
    response = await user_client.get("/admin/roles")
    assert response.status_code == 403


# --------- тесты получения данных  ---------


async def test_get_roles_returns_200_if_admin(admin_client, mock_access_service):
    """Ожидаем получить список ролей"""
    mock_role = MagicMock()
    mock_role.id = uuid.uuid4()
    mock_role.name = RoleName.MANAGER
    mock_role.description = "Менеджер(управляющий)"
    mock_access_service.get_all_roles.return_value = [mock_role]

    response = await admin_client.get("/admin/roles")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == RoleName.MANAGER


async def test_get_rules_for_role(admin_client, mock_access_service):
    """Проверка получения все правил на конкретную роль"""
    role_id = uuid.uuid4()
    mock_rule = MagicMock()
    mock_rule.id = uuid.uuid4()
    mock_rule.role_id = role_id
    mock_rule.element_id = uuid.uuid4()
    mock_rule.element_name = BusinessElementName.PRODUCTS
    mock_rule.element = MagicMock()
    mock_rule.can_read = True
    mock_rule.can_read_all = True
    mock_rule.can_create = False
    mock_rule.can_update = False
    mock_rule.can_update_all = False
    mock_rule.can_delete = False
    mock_rule.can_delete_all = False
    mock_access_service.get_rules_for_role.return_value = [mock_rule]

    response = await admin_client.get(f"/admin/roles/{role_id}/rules")

    assert response.status_code == 200
    mock_access_service.get_rules_for_role.assert_called_once_with(role_id)


# -------- тесты создания правил -----------


async def test_create_rule_success(admin_client, mock_access_service):
    """Проверка создания правила"""
    new_rule = MagicMock()
    new_rule.id = uuid.uuid4()
    new_rule.role_id = uuid.uuid4()
    new_rule.element_id = uuid.uuid4()
    new_rule.element_name = BusinessElementName.PRODUCTS
    new_rule.element = None
    new_rule.can_read = True
    new_rule.can_read_all = False
    new_rule.can_create = False
    new_rule.can_update = False
    new_rule.can_update_all = False
    new_rule.can_delete = False
    new_rule.can_delete_all = False
    mock_access_service.create_rule.return_value = new_rule

    response = await admin_client.post(
        "/admin/rules",
        json={
            "role_id": str(uuid.uuid4()),
            "element_id": str(uuid.uuid4()),
            "can_read": True,
            "can_read_all": True,
            "can_create": True,
            "can_update": True,
            "can_update_all": True,
            "can_delete": True,
            "can_delete_all": True,
        },
    )

    assert response.status_code == 201


async def test_create_duplicate_rule_returns_409(admin_client, mock_access_service):
    """
    Сервис бросает RuleAlreadyExistsError - роут должен вернуть 409 Conflict.
    """
    mock_access_service.create_rule.side_effect = RuleAlreadyExistsError()

    response = await admin_client.post(
        "/admin/rules",
        json={
            "role_id": str(uuid.uuid4()),
            "element_id": str(uuid.uuid4()),
            "can_read": True,
            "can_read_all": True,
            "can_create": True,
            "can_update": True,
            "can_update_all": True,
            "can_delete": True,
            "can_delete_all": True,
        },
    )

    assert response.status_code == 409


async def test_create_rule_for_admin_role_returns_403(
    admin_client, mock_access_service
):
    """
    Проверяем что админ не смог случайно себе поменять права
    CannotModifyAdminError - 403.
    """

    mock_access_service.create_rule.side_effect = CannotModifyAdminError()

    response = await admin_client.post(
        "/admin/rules",
        json={
            "role_id": str(uuid.uuid4()),
            "element_id": str(uuid.uuid4()),
            "can_read": True,
            "can_read_all": True,
            "can_create": True,
            "can_update": True,
            "can_update_all": True,
            "can_delete": True,
            "can_delete_all": True,
        },
    )

    assert response.status_code == 403


# --------- тесты обновления --------


async def test_update_rule_success(admin_client, mock_access_service):
    """Проверка обновления роли"""
    rule_id = uuid.uuid4()
    updated_rule = MagicMock()
    updated_rule.id = rule_id
    updated_rule.role_id = uuid.uuid4()
    updated_rule.element_id = uuid.uuid4()
    updated_rule.element_name = BusinessElementName.PRODUCTS
    updated_rule.element = None
    updated_rule.can_read = True
    updated_rule.can_read_all = False
    updated_rule.can_create = True
    updated_rule.can_update = False
    updated_rule.can_update_all = False
    updated_rule.can_delete = False
    updated_rule.can_delete_all = False
    mock_access_service.update_rule.return_value = updated_rule

    response = await admin_client.patch(
        f"/admin/rules/{rule_id}", json={"can_create": True}
    )

    assert response.status_code == 200


async def test_update_nonexistent_rule_returns_404(admin_client, mock_access_service):
    """
    Проверяем что бросит 404 ошибку из за отсутствия правила
    """
    mock_access_service.update_rule.side_effect = RuleNotFoundError()

    response = await admin_client.patch(
        f"/admin/rules/{uuid.uuid4()}", json={"can_read": True}
    )

    assert response.status_code == 404


# -------- тесты удаления -----------


async def test_delete_rule_success(admin_client, mock_access_service):
    """Успешное удаление - 204 No Content."""
    rule_id = uuid.uuid4()
    response = await admin_client.delete(f"/admin/rules/{rule_id}")
    assert response.status_code == 204


async def test_delete_nonexistent_rule_returns_404(admin_client, mock_access_service):
    """404 ошибка - нечего возвращать если нет такого правила"""
    mock_access_service.delete_rule.side_effect = RuleNotFoundError()

    response = await admin_client.delete(f"/admin/rules/{uuid.uuid4()}")
    assert response.status_code == 404
