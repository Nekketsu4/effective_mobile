from datetime import datetime, timedelta

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
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        return token
