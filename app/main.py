from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.settings import settings
from app.vector_store import ensure_collections


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await ensure_collections()
    yield


app = FastAPI(title="PDF Extractor", version="0.1.0", lifespan=lifespan)

from app.api import auth, domains, jobs, query, validation  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(domains.router, prefix="/api/v1")
app.include_router(validation.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")

app.mount("/uploads", StaticFiles(directory=settings.pdf_upload_dir), name="uploads")
