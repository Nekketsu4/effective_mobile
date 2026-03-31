import uuid

from pydantic import BaseModel

from app.models.business_element import BusinessElementName


class AccessRuleCreate(BaseModel):
    role_id: uuid.UUID
    element_id: uuid.UUID
    can_read: bool
    can_read_all: bool
    can_create: bool
    can_update: bool
    can_update_all: bool
    can_delete: bool
    can_delete_all: bool


class AccessRuleUpdate(BaseModel):
    """схема для метода PATCH"""

    can_read: bool | None = None
    can_read_all: bool | None = None
    can_create: bool | None = None
    can_update: bool | None = None
    can_update_all: bool | None = None
    can_delete: bool | None = None
    can_delete_all: bool | None = None


class AccessRuleResponse(BaseModel):
    id: uuid.UUID
    role_id: uuid.UUID
    element_id: uuid.UUID
    element_name: BusinessElementName | None = None
    can_read: bool
    can_read_all: bool
    can_create: bool
    can_update: bool
    can_update_all: bool
    can_delete: bool
    can_delete_all: bool

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str

    model_config = {"from_attributes": True}
