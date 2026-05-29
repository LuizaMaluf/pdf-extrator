from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_admin
from app.models.domain import Periodicity

router = APIRouter(tags=["domains"])


class KnownFieldRequest(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-z_]+$")
    description: str = Field(min_length=5)


class DomainRegistrationRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    organ: str
    context: str = Field(min_length=10)
    priority_sections: list[str] = Field(min_length=1, max_length=5)
    known_fields: list[KnownFieldRequest] = Field(min_length=2, max_length=8)
    periodicity: Periodicity


@router.get("/domains")
async def list_domains(
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[object]:
    raise NotImplementedError


@router.post("/domains", status_code=status.HTTP_201_CREATED)
async def register_domain(
    body: DomainRegistrationRequest,
    current_user: object = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError


@router.get("/domains/{domain_id}")
async def get_domain(
    domain_id: UUID,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError


@router.post("/domains/{domain_id}/schema/validate")
async def validate_schema(
    domain_id: UUID,
    current_user: object = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError
