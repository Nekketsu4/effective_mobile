import uuid

import pytest

from app.repositories.access_rule_repo import AccessRuleRepository
from app.models.role import Role
from app.models.business_element import BusinessElement, BusinessElementName


@pytest.fixture
async def role(db):
    """Создаем роль в самом тесте"""
    role = Role(name="manager", description="Управляющий")
    db.add(role)
    await db.flush()
    return role


@pytest.fixture
async def element(db):
    """Создаем бизнес-элемент в тесте"""
    el = BusinessElement(name=BusinessElementName.PRODUCTS, description="Товары")
    db.add(el)
    await db.flush()
    return el


@pytest.fixture
async def access_repo(db):
    return AccessRuleRepository(db)


@pytest.fixture
async def seeded_rule(db, access_repo, role, element):
    """Создаем правило доступа к ресурсу"""
    rule = await access_repo.create(
        role_id=role.id,
        element_id=element.id,
        can_read=True,
        can_read_all=True,
        can_create=False,
        can_update=False,
        can_update_all=False,
        can_delete=False,
        can_delete_all=False,
    )
    return rule


# ---------- тесты создания ------------


async def test_create_rule(access_repo, role, element):
    rule = await access_repo.create(
        role_id=role.id,
        element_id=element.id,
        can_read=True,
        can_read_all=False,
        can_create=True,
        can_update=False,
        can_update_all=False,
        can_delete=False,
        can_delete_all=False,
    )
    assert rule.id is not None
    assert rule.can_read is True
    assert rule.can_create is True
    assert rule.can_delete is False


# ---------- тесты поиска ----------


async def test_get_rule_by_role_and_element_name(access_repo, role, seeded_rule):
    """Делаем поиск по role_id и element_name"""
    rule = await access_repo.get_rule(
        role_id=role.id, element_name=BusinessElementName.PRODUCTS
    )
    assert rule is not None
    assert rule.can_read is True


async def test_get_rule_returns_none_if_not_found(access_repo, role):
    """
    Граничный случай - не заданы правила для следующего элемента
    Репозиторий вернет None вместо исключения
    Исключения ловить будет либо сервис либо зависимости
    """
    rule = await access_repo.get_rule(
        role_id=role.id,
        element_name=BusinessElementName.ORDERS,
    )
    assert rule is None


async def test_get_rules_by_role_returns_all_rules(access_repo, role, seeded_rule):
    """Получаем список ролей(Привелегия админа)"""
    rules = await access_repo.get_rules_by_role(role_id=role.id)
    assert isinstance(rules, list)
    assert len(rules) == 1


# ---------- тесты обновления -----------


async def test_update_rule_changes_permissions(access_repo, seeded_rule):
    updated = await access_repo.update(
        rule_id=seeded_rule.id, can_create=True, can_update=True
    )
    # обновлено
    assert updated.can_create is True
    assert updated.can_update is True
    # не обновлено
    assert updated.can_read is True
    assert updated.can_delete is False


async def test_returns_none_if_rule_nonexists(access_repo):
    result = await access_repo.update(rule_id=uuid.uuid4(), can_read=True)
    assert result is None


# -------- тесты удаления ---------


async def test_delete_rule(access_repo, role, seeded_rule):
    await access_repo.delete(seeded_rule.id)

    # проверим что правило удалено
    rule = await access_repo.get_rule(
        role_id=role.id, element_name=BusinessElementName.PRODUCTS
    )

    assert rule is None
