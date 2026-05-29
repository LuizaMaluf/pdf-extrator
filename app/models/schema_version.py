import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum as SAEnum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SchemaStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"


class SchemaVersion(Base):
    __tablename__ = "schema_versions"
    __table_args__ = (UniqueConstraint("domain_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domains.id"))
    version: Mapped[int]
    status: Mapped[SchemaStatus] = mapped_column(SAEnum(SchemaStatus), default=SchemaStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    domain: Mapped["Domain"] = relationship(back_populates="schema_versions")  # type: ignore[name-defined] # noqa: F821
    extraction_jobs: Mapped[list["ExtractionJob"]] = relationship(back_populates="schema_version")  # type: ignore[name-defined] # noqa: F821
