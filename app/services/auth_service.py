import uuid
from datetime import datetime, timedelta, timezone

from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.role_repo import RoleRepository
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_token


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        role_repo: RoleRepository,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.role_repo = role_repo

    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        middle_name: str | None = None,
    ):
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise EmailAlreadyExistsError("Такой пользователь уже есть")

        default_role = await self.role_repo.get_by_name("user")

        user = await self.user_repo.create(
            email=email,
            hashed_password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            role_id=default_role.id,
        )
        return user

    async def login(self, email: str, password: str) -> str:
        user = await self.user_repo.get_by_email(email)

        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Неверный email или пароль")

        if not user.is_active:
            raise InactiveUserError("Аккаунт деактивирован")

        token = create_token(user_id=str(user.id))

        await self.session_repo.create(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        return token

    async def logout(self, user_id: uuid.UUID) -> None:
        """
        Логаут -> удаляем все сессии пользователя
        Токены этого пользователя становятся невалидными
        """
        await self.session_repo.delete_by_user_id(user_id)

    async def soft_delete(self, user_id: uuid.UUID) -> None:
        """
        Мягкое удаление — ставим is_active=False.
        Запись в БД остаётся, пользователь просто не может войти.
        """
        await self.user_repo.soft_delete(user_id)

    async def update_profile(self, user_id: uuid.UUID, **kwargs):
        """Обновление профиля пользователя."""
        return await self.user_repo.update(user_id, **kwargs)
