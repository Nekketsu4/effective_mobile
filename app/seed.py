import asyncio

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.access_rule import AccessRule
from app.models.business_element import BusinessElement
from app.utils.password import hash_password


async def seed():
    async with AsyncSessionLocal() as db:
        #  Роли
        admin_role = Role(name="admin", description="Полный доступ")
        manager_role = Role(name="manager", description="Управление ресурсами")
        user_role = Role(name="user", description="Базовый доступ")
        guest_role = Role(name="guest", description="Только чтение")
        db.add_all([admin_role, manager_role, user_role, guest_role])
        await db.flush()

        # Бизнес объекты
        products = BusinessElement(name="products", description="Товары")
        orders = BusinessElement(name="orders", description="Заказы")
        users_el = BusinessElement(name="users", description="Пользователи")
        rules_el = BusinessElement(name="rules", description="Правила доступа")
        db.add_all([products, orders, users_el, rules_el])
        await db.flush()

        # Правила доступа
        rules = [
            # admin - полный доступ ко всему
            AccessRule(
                role_id=admin_role.id,
                element_id=products.id,
                can_read=True,
                can_read_all=True,
                can_create=True,
                can_update=True,
                can_update_all=True,
                can_delete=True,
                can_delete_all=True,
            ),
            AccessRule(
                role_id=admin_role.id,
                element_id=rules_el.id,
                can_read=True,
                can_read_all=True,
                can_create=True,
                can_update=True,
                can_update_all=True,
                can_delete=True,
                can_delete_all=True,
            ),
            # manager - может читать всё, но редактировать/удалять может только свое
            AccessRule(
                role_id=manager_role.id,
                element_id=products.id,
                can_read=True,
                can_read_all=True,
                can_create=True,
                can_update=True,
                can_update_all=False,
                can_delete=True,
                can_delete_all=False,
            ),
            # user - может читать и создавать только своё
            AccessRule(
                role_id=user_role.id,
                element_id=orders.id,
                can_read=True,
                can_read_all=False,
                can_create=True,
                can_update=True,
                can_update_all=False,
                can_delete=False,
                can_delete_all=False,
            ),
            # guest - только чтение
            AccessRule(
                role_id=guest_role.id,
                element_id=products.id,
                can_read=True,
                can_read_all=True,
                can_create=False,
                can_update=False,
                can_update_all=False,
                can_delete=False,
                can_delete_all=False,
            ),
        ]
        db.add_all(rules)

        # Тестовые пользователи
        users = [
            User(
                first_name="Илья",
                last_name="Севаненко",
                email="admin_test@mail.ru",
                hashed_password=hash_password("admin111"),
                role_id=admin_role.id,
            ),
            User(
                first_name="Ирина",
                last_name="Гурьянова",
                email="manager_test@mail.ru",
                hashed_password=hash_password("manager111"),
                role_id=manager_role.id,
            ),
            User(
                first_name="Кадыр",
                last_name="Азиев",
                email="user_test@mail.ru",
                hashed_password=hash_password("user111"),
                role_id=user_role.id,
            ),
        ]
        db.add_all(users)
        await db.commit()
        print("Записи созданы успешно")


if __name__ == "__main__":
    asyncio.run(seed())
