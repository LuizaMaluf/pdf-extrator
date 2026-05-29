import asyncio
import uuid

from celery import shared_task

from app.celery_app import celery_app  # noqa: F401 — garante que a app está registrada
from app.exceptions import ClaudeAPIRateLimitError, ExtractionFailedError


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ExtractionFailedError,),
)
def process_extraction_job(self: object, job_id: str) -> None:
    from app.extraction_orchestrator import ExtractionOrchestrator

    orchestrator = ExtractionOrchestrator()
    try:
        asyncio.run(orchestrator.run(uuid.UUID(job_id)))
    except ClaudeAPIRateLimitError as exc:
        raise self.retry(exc=exc, countdown=120)  # type: ignore[attr-defined]
