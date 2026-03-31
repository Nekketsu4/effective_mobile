import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Depends

from app.utils.jwt import TokenInvalidError
from app.dependencies import get_current_user, require_permission, require_admin
from app.models.business_element import BusinessElementName
from app.models.role import RoleName


# ------------------------------------------------------------------ #
# Вспомогательное тестовое приложение
#
# Мы не тестируем реальные роуты — тестируем сами зависимости.
# Создаём минимальное FastAPI приложение с одним эндпоинтом
# который использует тестируемую зависимость.
# Это позволяет проверить HTTP поведение зависимости изолированно
# от любой бизнес-логики роутов.
# ------------------------------------------------------------------ #

protected_app = FastAPI()


@protected_app.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    """Эндпоинт защищённый get_current_user."""
    return {"user_id": str(user.id)}


@protected_app.get("/permission-check")
async def permission_route(
    _=Depends(require_permission(BusinessElementName.PRODUCTS, "read")),
):
    """Эндпоинт защищённый require_permission."""
    return {"ok": True}


@protected_app.get("/admin-only")
async def admin_route(user=Depends(require_admin)):
    """Эндпоинт защищённый require_admin."""
    return {"role": user.role.name}


# ---------- Фабрики мок объектов --------------


def make_mock_user(role_name: RoleName = RoleName.USER, is_active: bool = True):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = f"{role_name.value}@test.com"
    user.is_active = is_active
    user.role_id = uuid.uuid4()
    user.role = MagicMock()
    user.role.name = role_name
    return user


# ------------ Тесты get_current_user -----------


async def test_get_current_user_no_token_returns_401():
    """
    Без заголовка Authorization FastAPI возвращает 401
    (HTTPBearer не нашёл схему Bearer).
    """
    async with AsyncClient(
        transport=ASGITransport(app=protected_app), base_url="http://test"
    ) as client:
        response = await client.get("/protected")
    assert response.status_code == 401


async def test_get_current_user_expired_token_returns_401():
    """
    Токен истёк — должен вернуть 401.
    Мокируем decode_token чтобы бросил TokenExpiredError.
    """
    from app.utils.jwt import TokenExpiredError

    with patch("app.dependencies.decode_token", side_effect=TokenExpiredError()):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer expired.jwt.token"}
            )
    assert response.status_code == 401
    assert "истек" in response.json()["detail"]


async def test_get_current_user_invalid_token_returns_401():
    """Подделанный или повреждённый токен — 401."""

    with patch("app.dependencies.decode_token", side_effect=TokenInvalidError()):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer tampered.token"}
            )
    assert response.status_code == 401
    assert "действителен" in response.json()["detail"]


async def test_get_current_user_no_sub_in_payload_returns_401():
    """
    Токен валидный но в payload нет поля 'sub'.
    Такой токен мог быть создан сторонним сервисом с другой структурой.
    """
    with patch("app.dependencies.decode_token", return_value={"data": "empty"}):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer valid.empty.token"}
            )
    assert response.status_code == 401
    assert "Некорректный токен" in response.json()["detail"]


async def test_get_current_user_session_not_found_returns_401():
    """
    Токен валидный и sub есть, но сессии в БД нет.
    Это значит пользователь разлогинился — токен инвалидирован.
    """
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = None  # сессии нет

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(uuid.uuid4())}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer logged.out.token"}
            )
    assert response.status_code == 401
    assert "Сессия" in response.json()["detail"]


async def test_get_current_user_user_not_found_returns_401():
    """
    Сессия есть, но пользователь не найден в БД.
    Редкий случай — например, если запись удалили напрямую из БД.
    """
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = MagicMock()  # сессия есть

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id.return_value = None  # пользователя нет

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(uuid.uuid4())}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
        patch("app.dependencies.UserRepository", return_value=mock_user_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer valid.token"}
            )
    assert response.status_code == 401


async def test_get_current_user_inactive_user_returns_401():
    """
    Пользователь найден, но is_active=False — аккаунт деактивирован.
    """
    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = MagicMock()

    inactive_user = make_mock_user(is_active=False)
    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id.return_value = inactive_user

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(uuid.uuid4())}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
        patch("app.dependencies.UserRepository", return_value=mock_user_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer valid.token"}
            )
    assert response.status_code == 401
    assert "деактивирован" in response.json()["detail"]


async def test_get_current_user_success_returns_user():
    """
    Всё хорошо — токен валидный, сессия есть, пользователь активен.
    Проверяем что зависимость возвращает пользователя
    и эндпоинт получает его корректно.
    """
    user = make_mock_user(RoleName.USER)

    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = MagicMock()

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id.return_value = user

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(user.id)}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
        patch("app.dependencies.UserRepository", return_value=mock_user_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected", headers={"Authorization": "Bearer valid.token"}
            )
    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)


# ------------ Тесты require_permission ------------


async def test_require_permission_no_rule_returns_403():
    """
    У роли пользователя нет правила для запрашиваемого элемента.
    Например, роль 'guest' пытается создать заказ — правила нет вообще.
    """
    user = make_mock_user(RoleName.GUEST)

    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = MagicMock()

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id.return_value = user

    mock_access_repo = AsyncMock()
    mock_access_repo.get_rule.return_value = None  # правила нет

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(user.id)}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
        patch("app.dependencies.UserRepository", return_value=mock_user_repo),
        patch("app.dependencies.AccessRuleRepository", return_value=mock_access_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/permission-check", headers={"Authorization": "Bearer valid.token"}
            )
    assert response.status_code == 403


async def test_require_permission_rule_exists_but_false_returns_403():
    """
    Правило есть, но can_read=False.
    Например, гость видит элемент в таблице access_rules,
    но поле can_read явно выставлено в False.
    """
    user = make_mock_user(RoleName.GUEST)

    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = MagicMock()

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id.return_value = user

    rule = MagicMock()
    rule.can_read = False  # явный запрет
    mock_access_repo = AsyncMock()
    mock_access_repo.get_rule.return_value = rule

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(user.id)}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
        patch("app.dependencies.UserRepository", return_value=mock_user_repo),
        patch("app.dependencies.AccessRuleRepository", return_value=mock_access_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/permission-check", headers={"Authorization": "Bearer valid.token"}
            )
    assert response.status_code == 403
    assert "products" in response.json()["detail"]


async def test_require_permission_success_returns_200():
    """
    Правило есть и can_read=True — запрос проходит.
    """
    user = make_mock_user(RoleName.USER)

    mock_session_repo = AsyncMock()
    mock_session_repo.get_by_token.return_value = MagicMock()

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id.return_value = user

    rule = MagicMock()
    rule.can_read = True
    mock_access_repo = AsyncMock()
    mock_access_repo.get_rule.return_value = rule

    with (
        patch("app.dependencies.decode_token", return_value={"sub": str(user.id)}),
        patch("app.dependencies.SessionRepository", return_value=mock_session_repo),
        patch("app.dependencies.UserRepository", return_value=mock_user_repo),
        patch("app.dependencies.AccessRuleRepository", return_value=mock_access_repo),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=protected_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/permission-check", headers={"Authorization": "Bearer valid.token"}
            )
    assert response.status_code == 200


# ----------- Тесты require_admin -----------


async def test_require_admin_non_admin_returns_403():
    """
    Пользователь с ролью 'user' пытается зайти на admin эндпоинт.
    require_admin проверяет role.name — если не ADMIN, бросает 403.
    """
    non_admin = make_mock_user(RoleName.USER)
    protected_app.dependency_overrides[get_current_user] = lambda: non_admin

    async with AsyncClient(
        transport=ASGITransport(app=protected_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/admin-only", headers={"Authorization": "Bearer valid.token"}
        )

    protected_app.dependency_overrides.clear()
    assert response.status_code == 403
    assert "администратора" in response.json()["detail"]


async def test_require_admin_manager_returns_403():
    """
    Граничный случай — manager не является admin.
    Проверяем что промежуточные роли тоже не проходят.
    """
    manager = make_mock_user(RoleName.MANAGER)
    protected_app.dependency_overrides[get_current_user] = lambda: manager

    async with AsyncClient(
        transport=ASGITransport(app=protected_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/admin-only", headers={"Authorization": "Bearer valid.token"}
        )

    protected_app.dependency_overrides.clear()
    assert response.status_code == 403


async def test_require_admin_success_returns_200():
    """
    Пользователь с ролью admin — проходит и получает данные.
    """
    admin = make_mock_user(RoleName.ADMIN)
    protected_app.dependency_overrides[get_current_user] = lambda: admin

    async with AsyncClient(
        transport=ASGITransport(app=protected_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/admin-only", headers={"Authorization": "Bearer valid.token"}
        )

    protected_app.dependency_overrides.clear()
    assert response.status_code == 200
