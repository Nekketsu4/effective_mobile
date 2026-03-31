import uuid

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    middle_name: str | None = None
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password_confirm")
    @classmethod
    def password_match(cls, value, info):
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Пароли не совпадают")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Схема для PATCH /auth/me — обновление профиля."""

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None


class UserWithRoleResponse(BaseModel):
    """
    Расширенная схема пользователя для admin эндпоинтов.
    Включает имя роли
    """

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None
    is_active: bool
    role_id: uuid.UUID
    role_name: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserWithRoleResponse":
        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            middle_name=user.middle_name,
            is_active=user.is_active,
            role_id=user.role_id,
            role_name=user.role.name if user.role else None,
        )


class AssignRoleRequest(BaseModel):
    """Схема для назначения роли пользователю."""

    role_id: uuid.UUID
