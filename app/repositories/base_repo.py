import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class BaseRepository:
    model = None

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, entity_id: uuid.UUID):
        result = await self.db.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()
