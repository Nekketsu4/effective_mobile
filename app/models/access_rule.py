import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Импортируем только для type checker
if TYPE_CHECKING:
    from app.models.business_element import BusinessElement
    from app.models.role import Role


class AccessRule(Base):
    __tablename__ = "access_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    element_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_elements.id"), nullable=False
    )
    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_read_all: Mapped[bool] = mapped_column(Boolean, default=False)
    can_create: Mapped[bool] = mapped_column(Boolean, default=False)
    can_update: Mapped[bool] = mapped_column(Boolean, default=False)
    can_update_all: Mapped[bool] = mapped_column(Boolean, default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False)
    can_delete_all: Mapped[bool] = mapped_column(Boolean, default=False)

    role: Mapped["Role"] = relationship("Role", back_populates="access_rules")
    element: Mapped["BusinessElement"] = relationship(
        "BusinessElement", back_populates="access_rules"
    )
