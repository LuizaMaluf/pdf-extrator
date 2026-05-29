from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.extraction_job import ExtractionJob, ExtractionJobStatus

router = APIRouter(tags=["jobs"])


class UploadResponse(BaseModel):
    job_id: UUID
    status: ExtractionJobStatus


class ConfirmDomainRequest(BaseModel):
    domain_id: UUID


@router.post("/pdfs", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    file: UploadFile,
    domain_id: UUID | None = None,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    raise NotImplementedError


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: UUID,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> object:
    raise NotImplementedError


@router.post("/jobs/{job_id}/confirm-domain", response_model=UploadResponse)
async def confirm_domain(
    job_id: UUID,
    body: ConfirmDomainRequest,
    current_user: object = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    raise NotImplementedError
