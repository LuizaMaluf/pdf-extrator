from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.schema_field import FieldType

router = APIRouter(tags=["validation"])


class CorrectionRequest(BaseModel):
    field_name: str
    corrected_value: object


class NewFieldRequest(BaseModel):
    name: str
    value: object
    type: FieldType


class ValidationSubmitRequest(BaseModel):
    corrections: list[CorrectionRequest] = []
    new_fields: list[NewFieldRequest] = []


@router.get("/jobs/{job_id}/validation")
async def get_validation(
    job_id: UUID,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError


@router.patch("/jobs/{job_id}/validation")
async def submit_validation(
    job_id: UUID,
    body: ValidationSubmitRequest,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError
