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
    id: str
    email: str
    first_name: str
    last_name: str
    middle_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}
