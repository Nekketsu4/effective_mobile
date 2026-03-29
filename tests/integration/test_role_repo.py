import pytest

from app.repositories.role_repo import RoleRepository
from app.models.role import Role, RoleName


@pytest.fixture
async def role_repo(db):
    return RoleRepository(db)


@pytest.fixture
async def seeded_role(db):
    """Создаем роль"""
    role = Role(name=RoleName.ADMIN, description="Админ (Полный доступ)")
    db.add(role)
    await db.flush()
    return role


async def test_get_role_by_name(role_repo, seeded_role):
    role = await role_repo.get_by_name("admin")
    assert role is not None
    assert role.name == seeded_role.name


async def test_get_role_by_id(role_repo, seeded_role):
    role = await role_repo.get_by_id(seeded_role.id)
    assert role is not None
    assert role.id == seeded_role.id


async def test_get_list_roles(role_repo, seeded_role):
    roles = await role_repo.get_all()
    assert isinstance(roles, list)
    assert len(roles) >= 1
