import uuid
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Role(StrEnum):
    ANALYST = "analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[Role] = mapped_column(SAEnum(Role))
