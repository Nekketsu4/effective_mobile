import uuid
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.access_rule import AccessRule


class RoleName(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(
        SAEnum(
            RoleName,
            name="role_name",
            create_type=True,
        ),
        nullable=False,
        unique=True,
    )
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship("User", back_populates="role")
    access_rules: Mapped[list["AccessRule"]] = relationship(
        "AccessRule", back_populates="role"
    )
