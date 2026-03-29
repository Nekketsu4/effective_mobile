from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import  UserRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.access_rule_repo import AccessRuleRepository
from app.repositories.access_rule_repo import BusinessElementName
from app.utils.jwt import decode_token, TokenInvalidError, TokenExpiredError
from app.models.user import User
from app.models.role import RoleName

bearer_scheme = HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истек"
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не действителен"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен"
        )

    # проверка что токен есть в БД
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_token(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия не найдена или завершена"
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован"
        )

    return user

def require_permission(element_name: BusinessElementName, action: str):
    """
    Сделаем замыкание чтобы была возможность передать параметры в Depeneds

    @router.get("/products")
    async def get_products(
        user = Depends(get_current_user),
        _ = Depends(require_permission(BusinessElementName.PRODUCTS, "read"))
    """
    async def permission_checker(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
    ):
        access_repo = AccessRuleRepository(db)
        rule = await access_repo.get_rule(
            role_id=current_user.role_id,
            element_name=element_name
        )

        # динамически проверяем разрешение
        # f"can_{action}" -> "create" -> rule.can_create
        permission_field = f"can_{action}"
        if not rule or not getattr(rule, permission_field, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Нет прав на действие {action} для {element_name}"
            )

        return permission_checker

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Зависимость для админ эндпоинтов"""
    if current_user.role.name != RoleName.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )

    return current_user
