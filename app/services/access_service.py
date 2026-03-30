import uuid

from app.models.role import RoleName
from app.repositories.access_rule_repo import AccessRuleRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.business_element_repo import BusinessElementRepository


class RuleAlreadyExistsError(Exception):
    pass


class RuleNotFoundError(Exception):
    pass


class CannotModifyAdminError(Exception):
    pass


class AccessService:
    def __init__(
        self,
        access_repo: AccessRuleRepository,
        role_repo: RoleRepository,
        element_repo: BusinessElementRepository,
    ):
        self.access_repo = access_repo
        self.role_repo = role_repo
        self.element_repo = element_repo

    async def _guard_admin_role(self, role_id: uuid.UUID):
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise RuleNotFoundError("Роль не найдена")
        if role.name == RoleName.ADMIN:
            raise CannotModifyAdminError("Нельзя менять права администратора")

    async def create_rule(
        self, role_id: uuid.UUID, element_id: uuid.UUID, **permissions
    ):
        """
        Делаем следующие проверки прежде чем создать правило
        1. Проверка что роль существует вообще
        2. Запрещаем трогать админа
        3. Проверяем что пара(роль + элемент) не дублируется
        """
        # 1ая и 2ая проверка
        await self._guard_admin_role(role_id)

        element = await self.element_repo.get_by_id(element_id)
        if not element:
            raise RuleNotFoundError("Бизнес-элемент не найден")

        # 3ая проверка
        existing = await self.access_repo.get_rule(
            role_id=role_id, element_name=element.name
        )
        if existing:
            raise RuleAlreadyExistsError(
                "Правило для этой роли и элемента уже существует"
            )

        return await self.access_repo.create(
            role_id=role_id, element_id=element_id, **permissions
        )

    async def update_rule(self, rule_id: uuid.UUID, role_id: uuid.UUID, **permissions):
        rule = await self.access_repo.get_by_id(rule_id)
        if not rule:
            raise RuleNotFoundError("Правило не найдено")

        # защищаем роль админа от изменений
        await self._guard_admin_role(role_id)

        return await self.access_repo.update(rule_id=rule_id, **permissions)

    async def delete_rule(self, rule_id: uuid.UUID, role_id: uuid.UUID):
        rule = await self.access_repo.get_by_id(rule_id)
        if not rule:
            raise RuleNotFoundError("Правило не найдено")

        # защищаем админа от удаления
        await self._guard_admin_role(role_id)
        await self.access_repo.delete(rule_id)

    async def get_rules_for_role(self, role_id: uuid.UUID):
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise RuleNotFoundError("Роль не найдена")
        return await self.access_repo.get_rules_by_role(role_id)
