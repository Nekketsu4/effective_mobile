import uuid

from app.models.role import RoleName
from app.repositories.user_repo import UserRepository
from app.repositories.role_repo import RoleRepository


class UserNotFoundError(Exception):
    pass


class RoleNotFoundError(Exception):
    pass


class CannotModifyAdminError(Exception):
    pass


class CannotDeleteSelfError(Exception):
    pass


class UserManagementService:
    """
    Сервис для административного управления пользователями.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
    ):
        self.user_repo = user_repo
        self.role_repo = role_repo

    async def get_all_users(self):
        return await self.user_repo.get_all()

    async def get_user_by_id(self, user_id: uuid.UUID):
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError("Пользователь не найден")
        return user

    async def assign_role(
        self,
        target_user_id: uuid.UUID,
        role_id: uuid.UUID,
    ):
        """
        Назначаем роль пользователю.

        Две защиты:
        1. Нельзя назначить роль пользователю у которого уже есть роль admin —
           это защита от конфликтов между администраторами.
        2. Назначаемая роль должна существовать в БД.
        """
        target_user = await self.user_repo.get_by_id(target_user_id)
        if not target_user:
            raise UserNotFoundError("Пользователь не найден")

        # нельзя трогать другого администратора
        if target_user.role.name == RoleName.ADMIN:
            raise CannotModifyAdminError("Нельзя изменить роль администратора")

        new_role = await self.role_repo.get_by_id(role_id)
        if not new_role:
            raise RoleNotFoundError("Роль не найдена")

        return await self.user_repo.update(target_user_id, role_id=role_id)

    async def delete_user(
        self,
        target_user_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ):
        """
        Мягкое удаление пользователя администратором.

        Две защиты:
        1. Нельзя удалить самого себя — администратор не должен иметь
        2. Нельзя удалить другого администратора — защита от конфликтов.
        """
        if target_user_id == current_user_id:
            raise CannotDeleteSelfError(
                "Нельзя удалить собственный аккаунт через этот эндпоинт. "
                "Используйте DELETE /auth/me"
            )

        target_user = await self.user_repo.get_by_id(target_user_id)
        if not target_user:
            raise UserNotFoundError("Пользователь не найден")

        if target_user.role.name == RoleName.ADMIN:
            raise CannotModifyAdminError("Нельзя удалить другого администратора")

        await self.user_repo.soft_delete(target_user_id)
