from celery import Celery

from app.settings import settings

celery_app = Celery(
    "pdf_extractor",
    broker=settings.redis_url,
    backend=settings.redis_url.replace("/0", "/1"),
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
