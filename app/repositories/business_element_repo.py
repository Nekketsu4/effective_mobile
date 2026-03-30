from sqlalchemy import select

from app.models.business_element import BusinessElement, BusinessElementName
from app.repositories.base_repo import BaseRepository


class BusinessElementRepository(BaseRepository):
    model = BusinessElement

    async def get_by_name(self, name: BusinessElementName) -> BusinessElement | None:
        result = await self.db.execute(
            select(BusinessElement).where(BusinessElement.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self):
        result = await self.db.execute(select(BusinessElement))
        return list(result.scalars().all())
