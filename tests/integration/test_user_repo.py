import pytest

from app.repositories.user_repo import UserRepository
from app.models.role import Role
from app.utils.password import hash_password


@pytest.fixture
async def role(db):
    # создаем роль
    role = Role(name="user", description="Базовый доступ")
    db.add(role)
    await db.flush()
    return role


@pytest.fixture
async def user_repo(db):
    return UserRepository(db)


# -------- Создаем пользователя --------


async def test_create_user(user_repo, role):
    user = await user_repo.create(
        email="create_test@mail.ru",
        hashed_password=hash_password("user123"),
        first_name="Кадыр",
        last_name="Азиев",
        role_id=role.id,
    )
    assert user.id is not None
    assert user.email == "create_test@mail.ru"
    assert user.is_active is True
    assert user.created_at is not None


# ------- Ищем пользователя --------


async def test_get_user_by_email(user_repo, role):
    await user_repo.create(
        email="get_by_email_test@mail.ru",
        hashed_password=hash_password("user123"),
        first_name="Илья",
        last_name="Севаненко",
        role_id=role.id,
    )
    found = await user_repo.get_by_email("get_by_email_test@mail.ru")
    assert found is not None
    assert found.email == "get_by_email_test@mail.ru"


async def test_get_none_by_email_if_not_found(user_repo):
    empty = await user_repo.get_by_email("empty@mail.ru")
    assert empty is None


# ------- Удаляем пользователя(мягкое удаление) ----------


async def test_soft_delete_sets_is_active_false(user_repo, role):
    user = await user_repo.create(
        email="delete_test@mail.ru",
        hashed_password=hash_password("user12345"),
        first_name="Ирина",
        last_name="Гурьянова",
        role_id=role.id,
    )
    await user_repo.soft_delete(user.id)
    deleted_user = await user_repo.get_by_email("delete_test@mail.ru")
    assert deleted_user.is_active is False
    # убеждаемся что пользователь не удален полностью из БД
    assert deleted_user is not None


# ------- Редактируем пользователя ----------


async def test_update_user(user_repo: UserRepository, role):
    user = await user_repo.create(
        email="update_test@mail.ru",
        hashed_password=hash_password("user12345"),
        first_name="Ирина",
        last_name="Гурьянова",
        role_id=role.id,
    )
    update_data = {
        "first_name": "Ульяна",
        "hashed_password": hash_password("newpass333"),
    }

    updated_user = await user_repo.update(user.id, **update_data)

    assert updated_user.first_name == "Ульяна"
    assert updated_user.hashed_password == update_data["hashed_password"]
