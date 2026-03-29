import uuid

from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

from app.models.access_rule import AccessRule
from app.models.business_element import BusinessElement, BusinessElementName
from app.repositories.base_repo import BaseRepository


class AccessRuleRepository(BaseRepository):
    model = AccessRule

    async def create(
        self,
        role_id: uuid.UUID,
        element_id: uuid.UUID,
        can_read=False,
        can_read_all=False,
        can_create=False,
        can_update=False,
        can_update_all=False,
        can_delete=False,
        can_delete_all=False,
    ) -> AccessRule:
        rule = AccessRule(
            role_id=role_id,
            element_id=element_id,
            can_read=can_read,
            can_read_all=can_read_all,
            can_create=can_create,
            can_update=can_update,
            can_update_all=can_update_all,
            can_delete=can_delete,
            can_delete_all=can_delete_all,
        )
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def get_rule(
        self,
        role_id: uuid.UUID,
        element_name: BusinessElementName,
    ) -> AccessRule | None:
        result = await self.db.execute(
            select(AccessRule)
            .join(BusinessElement, AccessRule.element_id == BusinessElement.id)
            .where(AccessRule.role_id == role_id, BusinessElement.name == element_name)
        )
        return result.scalar_one_or_none()

    async def get_rules_by_role(self, role_id: uuid.UUID) -> list[AccessRule]:
        """Получаем список правил с привязанными к ним бизнес элементам"""
        result = await self.db.execute(
            select(AccessRule)
            .options(joinedload(AccessRule.element))
            .where(AccessRule.role_id == role_id)
        )
        return list(result.scalars().all())

    async def update(self, rule_id: uuid.UUID, **kwargs) -> AccessRule | None:
        rule = await self.get_by_id(rule_id)
        if not rule:
            return None

        allowed_fields = {
            "can_read",
            "can_read_all",
            "can_create",
            "can_update",
            "can_update_all",
            "can_delete",
            "can_delete_all",
        }
        for key, value in kwargs.items():
            # делаем проверку,чтобы избежать вставки несуществующего поля
            if key in allowed_fields:
                setattr(rule, key, value)

        await self.db.flush()
        return rule

    async def delete(self, rule_id: uuid.UUID) -> None:
        await self.db.execute(delete(AccessRule).where(AccessRule.id == rule_id))

        await self.db.flush()
