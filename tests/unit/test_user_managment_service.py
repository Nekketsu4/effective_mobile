import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.role import RoleName
from app.services.user_management_service import (
    UserManagementService,
    UserNotFoundError,
    RoleNotFoundError,
    CannotModifyAdminError,
    CannotDeleteSelfError,
)


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.get_all.return_value = []
    repo.get_by_id.return_value = None
    return repo


@pytest.fixture
def mock_role_repo():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    return repo


@pytest.fixture
def service(mock_user_repo, mock_role_repo):
    return UserManagementService(
        user_repo=mock_user_repo,
        role_repo=mock_role_repo,
    )


def make_mock_user(role_name: RoleName = RoleName.USER):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = f"{role_name.value}@test.com"
    user.is_active = True
    user.role = MagicMock()
    user.role.name = role_name
    user.role_id = uuid.uuid4()
    return user


# ----------- get_all_users -----------


async def test_get_all_users_returns_list(service, mock_user_repo):
    mock_user_repo.get_all.return_value = [make_mock_user(), make_mock_user()]
    users = await service.get_all_users()
    assert len(users) == 2
    mock_user_repo.get_all.assert_called_once()


# ----------- get_user_by_id -----------


async def test_get_user_by_id_success(service, mock_user_repo):
    user = make_mock_user()
    mock_user_repo.get_by_id.return_value = user
    result = await service.get_user_by_id(user.id)
    assert result == user


async def test_get_user_by_id_not_found_raises_error(service, mock_user_repo):
    mock_user_repo.get_by_id.return_value = None
    with pytest.raises(UserNotFoundError):
        await service.get_user_by_id(uuid.uuid4())


# ----------- assign_role -----------


async def test_assign_role_success(service, mock_user_repo, mock_role_repo):
    """
    Назначаем новую роль обычному пользователю.
    Проверяем что user_repo.update вызван с правильными аргументами.
    """
    user = make_mock_user(RoleName.USER)
    new_role = MagicMock()
    new_role.id = uuid.uuid4()
    mock_user_repo.get_by_id.return_value = user
    mock_role_repo.get_by_id.return_value = new_role

    await service.assign_role(
        target_user_id=user.id,
        role_id=new_role.id,
    )
    mock_user_repo.update.assert_called_once_with(user.id, role_id=new_role.id)


async def test_assign_role_to_admin_raises_error(service, mock_user_repo):
    """
    Нельзя менять роль администратору.
    Это защита от конфликтов между администраторами системы.
    """
    admin = make_mock_user(RoleName.ADMIN)
    mock_user_repo.get_by_id.return_value = admin

    with pytest.raises(CannotModifyAdminError):
        await service.assign_role(
            target_user_id=admin.id,
            role_id=uuid.uuid4(),
        )
    mock_user_repo.update.assert_not_called()


async def test_assign_nonexistent_role_raises_error(
    service, mock_user_repo, mock_role_repo
):
    user = make_mock_user(RoleName.USER)
    mock_user_repo.get_by_id.return_value = user
    mock_role_repo.get_by_id.return_value = None  # роль не найдена

    with pytest.raises(RoleNotFoundError):
        await service.assign_role(
            target_user_id=user.id,
            role_id=uuid.uuid4(),
        )
    mock_user_repo.update.assert_not_called()


async def test_assign_role_user_not_found_raises_error(service, mock_user_repo):
    mock_user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await service.assign_role(
            target_user_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
        )


# ----------- delete_user -----------


async def test_delete_user_success(service, mock_user_repo):
    user = make_mock_user(RoleName.USER)
    mock_user_repo.get_by_id.return_value = user

    await service.delete_user(
        target_user_id=user.id,
        current_user_id=uuid.uuid4(),  # другой пользователь
    )
    mock_user_repo.soft_delete.assert_called_once_with(user.id)


async def test_delete_self_raises_error(service, mock_user_repo):
    """
    Нельзя удалить самого себя через admin эндпоинт.
    Для этого есть DELETE /auth/me.
    Проверяем что soft_delete вообще не вызывается.
    """
    user_id = uuid.uuid4()
    with pytest.raises(CannotDeleteSelfError):
        await service.delete_user(
            target_user_id=user_id,
            current_user_id=user_id,  # тот же самый id
        )
    mock_user_repo.soft_delete.assert_not_called()


async def test_delete_admin_raises_error(service, mock_user_repo):
    """
    Нельзя удалить другого администратора.
    """
    admin = make_mock_user(RoleName.ADMIN)
    mock_user_repo.get_by_id.return_value = admin

    with pytest.raises(CannotModifyAdminError):
        await service.delete_user(
            target_user_id=admin.id,
            current_user_id=uuid.uuid4(),
        )
    mock_user_repo.soft_delete.assert_not_called()


async def test_delete_nonexistent_user_raises_error(service, mock_user_repo):
    mock_user_repo.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await service.delete_user(
            target_user_id=uuid.uuid4(),
            current_user_id=uuid.uuid4(),
        )
