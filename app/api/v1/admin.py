import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.access_rule_schemas import (
    AccessRuleCreate,
    AccessRuleUpdate,
    AccessRuleResponse,
    RoleResponse,
)
from app.services.access_service import (
    AccessService,
    RuleAlreadyExistsError,
    RuleNotFoundError,
    CannotModifyAdminError,
)
from app.repositories.access_rule_repo import AccessRuleRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.business_element_repo import BusinessElementRepository
from app.dependencies import require_admin


router = APIRouter(prefix="/admin", tags=["admin"])


def get_access_service(db: AsyncSession = Depends(get_db)) -> AccessService:
    """Все зависимости в одной функции"""
    return AccessService(
        access_repo=AccessRuleRepository(db),
        role_repo=RoleRepository(db),
        element_repo=BusinessElementRepository(db),
    )


@router.get("/roles", response_model=list[RoleResponse])
async def get_roles(
    _=Depends(require_admin), service: AccessService = Depends(get_access_service)
):
    """
    Возвращаем список ролей
    Сперва require_admin - проверяет на права админа
    если False, то в сервис даже не нужно обращаться
    """
    return await service.get_all_roles()


@router.get("/roles/{role_id}/rules", response_model=list[AccessRuleResponse])
async def get_rules_for_role(
    role_id: uuid.UUID,
    _=Depends(require_admin),
    service: AccessService = Depends(get_access_service),
):
    """Получаем список правил закрепленных за указанной ролью"""
    try:
        return await service.get_rules_for_role(role_id)
    except RuleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/rules", response_model=AccessRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_rule(
    body: AccessRuleCreate,
    _=Depends(require_admin),
    service: AccessService = Depends(get_access_service),
):
    """Создаем правило."""
    try:
        rule = await service.create_rule(
            role_id=body.role_id,
            element_id=body.element_id,
            can_read=body.can_read,
            can_read_all=body.can_read_all,
            can_create=body.can_create,
            can_update=body.can_update,
            can_update_all=body.can_update_all,
            can_delete=body.can_delete,
            can_delete_all=body.can_delete_all,
        )
        return rule
    #     Перехватываем ошибки бизнес логики и
    #     переводим в коды HTTP)
    except CannotModifyAdminError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except RuleAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except RuleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/rules/{rule_id}", response_model=AccessRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    body: AccessRuleUpdate,
    _=Depends(require_admin),
    service: AccessService = Depends(get_access_service),
):
    """
    Для PATCH передаём только непустые поля.

    Например если передали {"can_read": true} —
    получим {"can_read": True}, а не
    {"can_read": True, "can_create": None, "can_update": None, ...}

    Сервис получает только реальные изменения.
    """
    try:
        existing_rule = await service.get_rule_by_id(rule_id)  # через сервис
        updates = body.model_dump(exclude_none=True)
        return await service.update_rule(
            rule_id=rule_id, role_id=existing_rule.role_id, **updates
        )
    except CannotModifyAdminError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except RuleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    _=Depends(require_admin),
    service: AccessService = Depends(get_access_service),
):
    try:
        existing_rule = await service.get_rule_by_id(rule_id)  # через сервис
        if not existing_rule:
            raise RuleNotFoundError("Правило не найдено")

        await service.delete_rule(rule_id=rule_id, role_id=existing_rule.role_id)
    except CannotModifyAdminError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except RuleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
