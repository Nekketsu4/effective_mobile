from fastapi import Depends, APIRouter
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.business_element import BusinessElementName


router = APIRouter(prefix="/mock", tags=["mock resources"])


@router.get("/products")
async def get_products(
    _=Depends(require_permission(BusinessElementName.PRODUCTS, "read")),
    current_user: User = Depends(get_current_user),
):
    """
    Используются захардкоженные данные(без БД),
    предварительно прогнав через проверку прав
    """
    items = {
        "items": [
            {"id": 1, "status": "delivered", "total": 500},
            {"id": 2, "status": "pending", "total": 35},
        ],
        "requested_by": current_user.email,
    }
    return items


@router.post("/orders")
async def create_order(
    _=Depends(require_permission(BusinessElementName.ORDERS, "create")),
    current_user: User = Depends(get_current_user),
):
    return {"message": f"Заказ создан пользователем {current_user.email}"}
