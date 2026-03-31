from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth_schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.role_repo import RoleRepository
from app.dependencies import get_current_user
from app.models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Все зависимости в одной функции"""
    return AuthService(
        user_repo=UserRepository(db),
        session_repo=SessionRepository(db),
        role_repo=RoleRepository(db),
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest, service: AuthService = Depends(get_auth_service)
):
    try:
        user = await service.register(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            middle_name=data.middle_name,
        )
        return user
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    try:
        token = await service.login(email=data.email, password=data.password)
        return TokenResponse(access_token=token)
    except (InvalidCredentialsError, InactiveUserError) as e:
        # возвращаем две ошибки с 401 ответом, чтобы скрыть детали
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Удаляем сессию из БД"""
    await service.logout(user_id=current_user.id)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Обновление профиля текущего пользователя."""
    updates = body.model_dump(exclude_unset=True)
    return await service.update_profile(current_user.id, **updates)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Мягкое удаление аккаунта текущего пользователя.

    Два действия в одной операции:
    1. Разлогиниваем — удаляем все сессии (пользователь больше не может войти
       даже если знает пароль, пока is_active=False)
    2. Деактивируем — ставим is_active=False
    """
    await service.logout(user_id=current_user.id)
    await service.soft_delete(user_id=current_user.id)
