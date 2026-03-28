from sqlalchemy import select

from app.models.role import Role
from app.repositories.base_repo import BaseRepository


class RoleRepository(BaseRepository):
    model = Role

    async def get_by_name(self, name: str) -> Role | None:
        role = await self.db.execute(select(Role).where(Role.name == name))
        return role.scalar_one_or_none()

    async def get_all(self):
        roles = await self.db.execute(select(Role))
        return list(roles.scalars().all())
