import uuid

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.user import User
from app.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository):
    model = User

    async def create(
        self,
        email: str,
        hashed_password: str,
        first_name: str,
        last_name: str,
        role_id: uuid.UUID,
        middle_name: str | None = None,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            role_id=role_id,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_by_id(self, entity_id: uuid.UUID) -> User | None:
        """
        Перекрываем базовый get_by_id чтобы загружать role вместе с пользователем.

        joinedload делает LEFT OUTER JOIN с таблицей roles в одном запросе.
        Без этого SQLAlchemy использует lazy loading — подгружает role отдельным
        запросом при первом обращении к user.role.
        """
        result = await self.db.execute(
            select(User).options(joinedload(User.role)).where(User.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        user = await self.db.execute(select(User).where(User.email == email))
        return user.scalar_one_or_none()

    async def soft_delete(self, user_id: uuid.UUID):
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = False
            await self.db.flush()

    async def update(self, user_id: uuid.UUID, **kwargs) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        await self.db.flush()
        return user

    async def get_all(self) -> list[User]:
        """Загружаем всех пользователей сразу"""
        result = await self.db.execute(select(User).options(joinedload(User.role)))
        return list(result.scalars().all())
