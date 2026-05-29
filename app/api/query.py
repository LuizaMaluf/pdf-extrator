from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db

router = APIRouter(tags=["query"])


@router.get("/domains/{domain_id}/extractions")
async def list_extractions(
    domain_id: UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    schema_version: int | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError
