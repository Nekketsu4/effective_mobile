import uuid
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.access_rule import AccessRule


class BusinessElementName(str, enum.Enum):

    PRODUCTS = "products"
    ORDERS = "orders"
    USERS = "users"
    ACCESS_RULES = "access_rule"


class BusinessElement(Base):
    __tablename__ = "business_elements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(
        SAEnum(
            BusinessElementName,
            name="business_element_name",
            create_type=True
        ),
        unique=True,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text)

    access_rules: Mapped[list["AccessRule"]] = relationship(
        "AccessRule", back_populates="element"
    )
