import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum as SAEnum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from app.database import Base


class ExtractionJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    NEEDS_CONFIRMATION = "needs_confirmation"
    NEEDS_REGISTRATION = "needs_registration"
    COMPLETED = "completed"
    VALIDATED = "validated"
    FAILED = "failed"


class Daterange(UserDefinedType):
    """PostgreSQL daterange type."""

    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "daterange"


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pdf_path: Mapped[str]
    domain_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("domains.id"), default=None)
    schema_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("schema_versions.id"), default=None
    )
    status: Mapped[ExtractionJobStatus] = mapped_column(
        SAEnum(ExtractionJobStatus), default=ExtractionJobStatus.PENDING
    )
    confidence: Mapped[float | None] = mapped_column(default=None)
    period_reference: Mapped[object | None] = mapped_column(Daterange, default=None)
    result: Mapped[dict | None] = mapped_column(JSONB, default=None)
    error: Mapped[str | None] = mapped_column(default=None)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    domain: Mapped["Domain | None"] = relationship(back_populates="extraction_jobs")  # type: ignore[name-defined] # noqa: F821
    schema_version: Mapped["SchemaVersion | None"] = relationship(back_populates="extraction_jobs")  # type: ignore[name-defined] # noqa: F821
    corrections: Mapped[list["Correction"]] = relationship(back_populates="job")  # type: ignore[name-defined] # noqa: F821
