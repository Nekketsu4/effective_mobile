import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InactiveUserError,
)

from app.utils.password import hash_password


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    return repo


@pytest.fixture
def mock_session_repo():
    return AsyncMock()


@pytest.fixture
def mock_role_repo():
    repo = AsyncMock()
    role = MagicMock()
    role.id = "mock_id"
    role.name = "user"
    repo.get_by_name.return_value = role
    return repo


@pytest.fixture
def auth_service(mock_user_repo, mock_session_repo, mock_role_repo):
    return AuthService(
        user_repo=mock_user_repo,
        session_repo=mock_session_repo,
        role_repo=mock_role_repo,
    )


# ----------- Тесты регистрации -----------


async def test_register_success(auth_service, mock_user_repo):
    await auth_service.register(
        email="register_user@mail.ru",
        password=hash_password("reg_user123"),
        first_name="Сегрей",
        last_name="Вагабов",
    )
    # проверка вызова репозитория
    mock_user_repo.create.assert_called_once()


async def test_register_hashes_password(auth_service, mock_user_repo):
    await auth_service.register(
        email="register_user1@mail.ru",
        password="unhashed_user123",
        first_name="Федор",
        last_name="Кузнецов",
    )
    call_kwargs = mock_user_repo.create.call_args.kwargs
    assert call_kwargs["hashed_password"] != "unhashed_user123"


# ----------- Тесты регистрации -----------


async def test_return_token_if_login_success(auth_service, mock_user_repo):
    user = MagicMock()
    user.id = "some_user_uuid"
    user.is_active = True
    user.hashed_password = hash_password("login_success_pass123")
    mock_user_repo.get_by_email.return_value = user

    token = await auth_service.login(
        email="success@mail.ru", password="login_success_pass123"
    )
    assert token is not None
    assert isinstance(token, str)


async def test_raises_error_if_wrong_password(auth_service, mock_user_repo):
    user = MagicMock()
    user.id = "some_user_uuid"
    user.is_active = True
    user.hashed_password = hash_password("correct_pass123")
    mock_user_repo.get_by_email.return_value = user

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(email="fail@mail.ru", password="wrong_pass123")


async def test_raises_error_if_login_inactive_user(auth_service, mock_user_repo):
    user = MagicMock()
    user.is_active = False
    user.hashed_password = hash_password("deleted_user_pass123")
    mock_user_repo.get_by_email.return_value = user

    with pytest.raises(InactiveUserError):
        await auth_service.login(
            email="deleted_user@mail.ru", password="deleted_user_pass123"
        )


async def test_raises_error_if_nonexists_user(auth_service, mock_user_repo):
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login("nonexist@mail.ru", password="nonexist_pass123")
