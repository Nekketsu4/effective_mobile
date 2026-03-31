import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role, RoleName
from app.models.access_rule import AccessRule
from app.models.business_element import BusinessElement, BusinessElementName
from app.utils.password import hash_password


async def get_or_create_role(db, name: RoleName, description: str) -> Role:
    """
    Ищем роль по имени. Если не нашли — создаём.
    Это и есть идемпотентность: повторный запуск не создаёт дубликаты.
    """
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if not role:
        role = Role(name=name, description=description)
        db.add(role)
        await db.flush()
        print(f"  Создана роль: {name.value}")
    else:
        print(f"  Роль уже существует: {name.value}")
    return role


async def get_or_create_element(
    db, name: BusinessElementName, description: str
) -> BusinessElement:
    """
    То же самое для бизнес-элементов.
    """
    result = await db.execute(
        select(BusinessElement).where(BusinessElement.name == name)
    )
    element = result.scalar_one_or_none()
    if not element:
        element = BusinessElement(name=name, description=description)
        db.add(element)
        await db.flush()
        print(f"  Создан элемент: {name.value}")
    else:
        print(f"  Элемент уже существует: {name.value}")
    return element


async def get_or_create_rule(db, role_id, element_id, **permissions) -> AccessRule:
    """
    Правило уникально по паре (role_id, element_id).
    Если такое правило уже есть — не трогаем его.
    Это важно: если админ поменял права через API,
    повторный запуск seed не перезатрёт его изменения.
    """
    result = await db.execute(
        select(AccessRule).where(
            AccessRule.role_id == role_id,
            AccessRule.element_id == element_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        rule = AccessRule(role_id=role_id, element_id=element_id, **permissions)
        db.add(rule)
        await db.flush()
        print(f"  Создано правило для role={role_id}, element={element_id}")
    else:
        print(f"  Правило уже существует для role={role_id}, element={element_id}")
    return rule


async def get_or_create_user(db, email: str, role_id, **kwargs) -> User:
    """
    Пользователь уникален по email.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, role_id=role_id, **kwargs)
        db.add(user)
        await db.flush()
        print(f"  Создан пользователь: {email}")
    else:
        print(f"  Пользователь уже существует: {email}")
    return user


async def seed():
    print("=== Запуск seed ===")
    async with AsyncSessionLocal() as db:
        print("\n[1/4] Роли...")
        admin_role = await get_or_create_role(
            db, RoleName.ADMIN, "Админ (Полный доступ)"
        )
        manager_role = await get_or_create_role(
            db, RoleName.MANAGER, "Управляющий (Управление ресурсами)"
        )
        user_role = await get_or_create_role(
            db, RoleName.USER, "Пользователь (Базовый доступ)"
        )
        guest_role = await get_or_create_role(
            db, RoleName.GUEST, "Гость (Только чтение)"
        )

        print("\n[2/4] Бизнес-элементы...")
        products = await get_or_create_element(
            db, BusinessElementName.PRODUCTS, "Товары"
        )
        orders = await get_or_create_element(db, BusinessElementName.ORDERS, "Заказы")
        users_el = await get_or_create_element(
            db, BusinessElementName.USERS, "Пользователи"
        )
        rules_el = await get_or_create_element(
            db, BusinessElementName.ACCESS_RULES, "Правила доступа"
        )

        print("\n[3/4] Правила доступа...")
        # admin — полный доступ ко всему
        await get_or_create_rule(
            db,
            admin_role.id,
            products.id,
            can_read=True,
            can_read_all=True,
            can_create=True,
            can_update=True,
            can_update_all=True,
            can_delete=True,
            can_delete_all=True,
        )
        await get_or_create_rule(
            db,
            admin_role.id,
            rules_el.id,
            can_read=True,
            can_read_all=True,
            can_create=True,
            can_update=True,
            can_update_all=True,
            can_delete=True,
            can_delete_all=True,
        )
        # manager — читает всё, редактирует/удаляет только своё
        await get_or_create_rule(
            db,
            manager_role.id,
            products.id,
            can_read=True,
            can_read_all=True,
            can_create=True,
            can_update=True,
            can_update_all=False,
            can_delete=True,
            can_delete_all=False,
        )
        # user — читает и создаёт только своё
        await get_or_create_rule(
            db,
            user_role.id,
            orders.id,
            can_read=True,
            can_read_all=False,
            can_create=True,
            can_update=True,
            can_update_all=False,
            can_delete=False,
            can_delete_all=False,
        )
        # guest — только чтение
        await get_or_create_rule(
            db,
            guest_role.id,
            products.id,
            can_read=True,
            can_read_all=True,
            can_create=False,
            can_update=False,
            can_update_all=False,
            can_delete=False,
            can_delete_all=False,
        )

        print("\n[4/4] Тестовые пользователи...")
        await get_or_create_user(
            db,
            "admin_test@mail.ru",
            admin_role.id,
            first_name="Илья",
            last_name="Севаненко",
            hashed_password=hash_password("admin111"),
        )
        await get_or_create_user(
            db,
            "manager_test@mail.ru",
            manager_role.id,
            first_name="Ирина",
            last_name="Гурьянова",
            hashed_password=hash_password("manager111"),
        )
        await get_or_create_user(
            db,
            "user_test@mail.ru",
            user_role.id,
            first_name="Кадыр",
            last_name="Азиев",
            hashed_password=hash_password("user111"),
        )

        await db.commit()
        print("\n=== Seed завершён успешно ===")


if __name__ == "__main__":
    asyncio.run(seed())
