import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("extraction_jobs.id"))
    field_name: Mapped[str]
    original_value: Mapped[dict | None] = mapped_column(JSONB, default=None)
    corrected_value: Mapped[dict] = mapped_column(JSONB)
    is_new_field: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    job: Mapped["ExtractionJob"] = relationship(back_populates="corrections")  # type: ignore[name-defined] # noqa: F821
