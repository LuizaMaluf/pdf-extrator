import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum as SAEnum, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Periodicity(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(unique=True)
    organ: Mapped[str]
    context: Mapped[str]
    priority_sections: Mapped[list[str]] = mapped_column(ARRAY(TEXT))
    known_fields: Mapped[dict] = mapped_column(JSONB)
    periodicity: Mapped[Periodicity] = mapped_column(SAEnum(Periodicity))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    schema_versions: Mapped[list["SchemaVersion"]] = relationship(back_populates="domain")  # type: ignore[name-defined] # noqa: F821
    schema_fields: Mapped[list["SchemaField"]] = relationship(back_populates="domain")  # type: ignore[name-defined] # noqa: F821
    extraction_jobs: Mapped[list["ExtractionJob"]] = relationship(back_populates="domain")  # type: ignore[name-defined] # noqa: F821
