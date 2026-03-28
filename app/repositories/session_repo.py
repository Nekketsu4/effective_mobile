import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.models.session import Session
from app.repositories.base_repo import BaseRepository


class SessionRepository(BaseRepository):
    model = Session

    async def create(
        self, user_id: uuid.UUID, token: str, expires_at: datetime
    ) -> Session:
        session = Session(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_token(self, token: str) -> Session | None:
        """Ищем сессию по токену и сразу отсеиваем истекшие токены"""
        session = await self.db.execute(
            select(Session).where(
                Session.token == token, Session.expires_at > datetime.utcnow()
            )
        )
        return session.scalar_one_or_none()

    async def delete_by_user_id(self, user_id: uuid.UUID) -> None:
        await self.db.execute(delete(Session).where(Session.user_id == user_id))
        await self.db.flush()
