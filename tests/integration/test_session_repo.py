import pytest
from datetime import datetime, timedelta

from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.models.role import Role
from app.utils.password import hash_password


@pytest.fixture
async def user(db):
    """Создаем пользователя, чтобы взаимодействовать с сессиями"""
    role = Role(name="user", description="Базовый доступ")
    db.add(role)
    await db.flush()

    user_repo = UserRepository(db)
    user = await user_repo.create(
        email="session_user@mail.ru",
        hashed_password=hash_password("session123"),
        first_name="Олег",
        last_name="Селезнев",
        role_id=role.id,
    )
    return user


@pytest.fixture
async def session_repo(db):
    return SessionRepository(db)


async def test_create_session(session_repo, user):
    session = await session_repo.create(
        user_id=user.id,
        token="some.jwt.token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    assert session.id is not None
    assert session.token == "some.jwt.token"
    assert session.user_id == user.id


async def get_session_by_token(session_repo, user):
    await session_repo.create(
        user_id=user.id,
        token="some_1.jwt.token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    found_session = await session_repo.get_by_token("some_1.jwt.token")
    assert found_session is not None
    assert found_session.token == "some_1.jwt.token"


async def test_get_none_by_token_if_token_not_exists(session_repo):
    empty = await session_repo.get_by_token("nonexists.jwt.token")
    assert empty is None


async def test_remove_sessions_delete_by_user_id(session_repo, user):
    """Тест удаления всех сессий при логауте пользователя"""
    await session_repo.create(
        user_id=user.id,
        token="device_1.jwt.token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    await session_repo.create(
        user_id=user.id,
        token="device_2.jwt.token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )

    await session_repo.delete_by_user_id(user.id)

    # созданные сессии удаляются
    assert await session_repo.get_by_token("device_1.jwt.token") is None
    assert await session_repo.get_by_token("device_2.jwt.token") is None


async def test_returns_none_if_session_expired(session_repo, user):
    """Тест что истекший токен не работает"""
    await session_repo.create(
        user_id=user.id,
        token="expired.jwt.token",
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    expired_token = await session_repo.get_by_token("expired.jwt.token")
    assert expired_token is None
