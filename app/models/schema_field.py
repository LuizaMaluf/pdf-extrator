import uuid
from enum import StrEnum

from sqlalchemy import Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FieldType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    TABLE = "table"


class FieldStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class SchemaField(Base):
    __tablename__ = "schema_fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domains.id"))
    name: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    field_type: Mapped[FieldType] = mapped_column(SAEnum(FieldType), default=FieldType.STRING)
    status: Mapped[FieldStatus] = mapped_column(SAEnum(FieldStatus), default=FieldStatus.ACTIVE)
    added_in_version: Mapped[int]
    deprecated_in_version: Mapped[int | None] = mapped_column(default=None)

    domain: Mapped["Domain"] = relationship(back_populates="schema_fields")  # type: ignore[name-defined] # noqa: F821
