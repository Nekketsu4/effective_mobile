import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.role import RoleName
from app.services.access_service import (
    AccessService,
    RuleAlreadyExistsError,
    RuleNotFoundError,
    CannotModifyAdminError,
)


@pytest.fixture
def mock_access_repo():
    repo = AsyncMock()
    repo.get_rule.return_value = None
    return repo


@pytest.fixture
def mock_role_repo():
    repo = AsyncMock()
    role = MagicMock()
    role.id = uuid.uuid4()
    role.name = RoleName.MANAGER
    repo.get_rule.return_value = role
    return repo


@pytest.fixture
def mock_element_repo():
    repo = AsyncMock()
    element = MagicMock()
    element.id = uuid.uuid4()
    repo.get_by_id.return_value = element
    return repo


@pytest.fixture
def access_service(mock_access_repo, mock_role_repo, mock_element_repo):
    return AccessService(
        access_repo=mock_access_repo,
        role_repo=mock_role_repo,
        element_repo=mock_element_repo,
    )


# ------------ тесты создания правил ------------


async def test_create_rule_success(access_service, mock_access_repo):
    await access_service.create_rule(
        role_id=uuid.uuid4(), element_id=uuid.uuid4(), can_read=True
    )
    mock_access_repo.create.assert_called_once()


async def test_create_duplicate_rule_raises_error(access_service, mock_access_repo):
    """
    Сервис проверит через AccessRuleRepository.get_rule
    существует ли такое правило или нет.
    Сервис поймает это исключение еще до того
    как произойдет AccessRuleRepositor.create
    """
    mock_access_repo.get_rule.return_value = MagicMock()

    with pytest.raises(RuleAlreadyExistsError):
        await access_service.create_rule(
            role_id=uuid.uuid4(), element_id=uuid.uuid4(), can_read=True
        )
    mock_access_repo.create.assert_not_called()


async def test_create_rule_raise_error_if_role_not_exists(
    access_service, mock_role_repo
):
    mock_role_repo.get_by_id.return_value = None  # не нашли роль

    with pytest.raises(RuleNotFoundError):
        await access_service.create_rule(
            role_id=uuid.uuid4(), element_id=uuid.uuid4(), can_read=True
        )


# ----------- тест защиты роли админа ----------


async def test_cannot_modify_admin_role_rules(
    access_service, mock_role_repo, mock_access_repo
):
    """Проверка защиты на изменение правил роли админа"""
    admin_role = MagicMock()
    admin_role.name = RoleName.ADMIN
    mock_role_repo.get_by_id.return_value = admin_role

    existing_rule = MagicMock()
    existing_rule.id = uuid.uuid4()
    mock_access_repo.get_by_id.return_value = existing_rule

    with pytest.raises(CannotModifyAdminError):
        await access_service.update_rule(
            rule_id=existing_rule.id, role_id=admin_role.id, can_read=False
        )


# ---------- тесты обновления -------------


async def test_update_rule_success(access_service, mock_access_repo, mock_role_repo):
    rule = MagicMock()
    rule.id = uuid.uuid4()
    mock_access_repo.get_by_id.return_value = rule

    await access_service.update_rule(
        rule_id=rule.id, role_id=uuid.uuid4(), can_read=True, can_create=True
    )
    mock_access_repo.update.assert_called_once()


async def test_update_raise_error_if_rule_not_exists(access_service, mock_access_repo):
    mock_access_repo.get_by_id.return_value = None  # Правило не найдено

    with pytest.raises(RuleNotFoundError):
        await access_service.update_rule(
            rule_id=uuid.uuid4(), role_id=uuid.uuid4(), can_read=True
        )
