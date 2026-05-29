---
name: python-stack-patterns
description: Use this skill whenever writing or reviewing code that touches FastAPI routes, SQLAlchemy async sessions, Celery tasks, Qdrant client calls, sentence-transformers, or Docker Compose in this project. Enforces stack-specific patterns tailored to the PDF Extractor architecture. Trigger on: "implement endpoint", "write a celery task", "add a route", "query the database", "search qdrant", "generate embeddings", "write docker compose", or any time stack-specific implementation is happening.
---

# Python Stack Patterns

Padrões específicos para o stack do PDF Extractor. Cada seção mapeia a um componente do sistema — consulte a seção relevante para o que você está implementando.

---

## Tooling

```toml
# pyproject.toml — use uv para gerenciar dependências
[tool.ruff]
line-length = 88
select = ["E", "F", "I", "UP"]  # pycodestyle, pyflakes, isort, pyupgrade

[tool.ruff.lint]
select = ["ALL"]
ignore = ["D", "ANN101"]
```

```bash
uv add fastapi sqlalchemy alembic celery redis qdrant-client \
       sentence-transformers anthropic pdfplumber camelot-py \
       python-jose[cryptography] passlib[bcrypt]
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

---

## 1. FastAPI

### Estrutura de rotas

Rotas são coordenadoras — sem lógica de negócio. Toda lógica fica nos componentes de `src/`.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from app.dependencies import get_current_user, require_admin
from app.schemas import ExtractionJobResponse, UploadResponse
from app.extraction_orchestrator import ExtractionOrchestrator

router = APIRouter(prefix="/pdfs", tags=["jobs"])

@router.post("/", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    file: UploadFile,
    domain_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    orchestrator: ExtractionOrchestrator = Depends(),
) -> UploadResponse:
    job_id = await orchestrator.enqueue(file, domain_id, current_user.id)
    return UploadResponse(job_id=job_id, status=ExtractionJobStatus.PENDING)
```

### Dependency injection

Auth e sessão de banco via `Depends` — nunca instancie diretamente em rotas.

```python
# app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_jwt(token)
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return current_user
```

### Pydantic V2 schemas

Schemas de request/response separados dos modelos ORM. Nunca exponha modelos SQLAlchemy diretamente.

```python
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime

class ExtractionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Pydantic V2

    job_id: UUID
    status: ExtractionJobStatus
    domain_id: UUID | None = None
    confidence: float | None = None
    result: dict | None = None
    created_at: datetime

class DomainRegistrationRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    organ: str
    context: str = Field(min_length=10)
    priority_sections: list[str] = Field(min_length=1, max_length=5)
    known_fields: list[KnownField] = Field(min_length=2, max_length=8)
    periodicity: Periodicity
```

---

## 2. SQLAlchemy 2.0 Async

### Engine e session factory

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://...
    pool_size=10,
    max_overflow=20,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # evita lazy loading após commit
)

class Base(DeclarativeBase):
    pass
```

### Modelos ORM

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Enum as SAEnum
import uuid

class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("domains.id"))
    status: Mapped[ExtractionJobStatus] = mapped_column(
        SAEnum(ExtractionJobStatus), default=ExtractionJobStatus.PENDING
    )
    confidence: Mapped[float | None]
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    domain: Mapped["Domain | None"] = relationship(back_populates="jobs")
```

### Queries

Use `select()` do SQLAlchemy 2.0 — nunca `session.query()` (API legada).

```python
from sqlalchemy import select

async def get_active_schema(db: AsyncSession, domain_id: UUID) -> SchemaVersion:
    result = await db.execute(
        select(SchemaVersion)
        .where(SchemaVersion.domain_id == domain_id)
        .order_by(SchemaVersion.version.desc())
        .limit(1)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise DomainNotFoundError(domain_id)
    return schema
```

---

## 3. Celery

### Definição de task

```python
# app/tasks.py
from celery import shared_task
from app.extraction_orchestrator import ExtractionOrchestrator
import uuid

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ExtractionFailedError,),
)
def process_extraction_job(self, job_id: str) -> None:
    orchestrator = ExtractionOrchestrator()
    try:
        orchestrator.run(uuid.UUID(job_id))
    except ClaudeAPIRateLimitError as exc:
        raise self.retry(exc=exc, countdown=120)
```

### Configuração

```python
# app/celery_app.py
from celery import Celery

celery_app = Celery(
    "pdf_extractor",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,        # só confirma após sucesso
    worker_prefetch_multiplier=1,  # um job por worker (extrações são pesadas)
)
```

---

## 4. Qdrant

### Client setup

```python
# app/vector_store.py
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance

qdrant_client = AsyncQdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
)

async def ensure_collections() -> None:
    for name, size in [("domain_signatures", 768), ("few_shot_examples", 768)]:
        if not await qdrant_client.collection_exists(name):
            await qdrant_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
```

### Busca com filtro de domínio

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

async def search_few_shot_examples(
    embedding: list[float],
    domain_id: UUID,
    limit: int = MAX_FEW_SHOT_EXAMPLES,
    score_threshold: float = MIN_FEW_SHOT_SCORE,
) -> list[FewShotExample]:
    results = await qdrant_client.search(
        collection_name="few_shot_examples",
        query_vector=embedding,
        query_filter=Filter(
            must=[FieldCondition(key="domain_id", match=MatchValue(value=str(domain_id)))]
        ),
        score_threshold=score_threshold,
        limit=limit,
    )
    return [FewShotExample(**r.payload, score=r.score) for r in results]
```

---

## 5. sentence-transformers

```python
from sentence_transformers import SentenceTransformer
from functools import lru_cache

EMBEDDING_MODEL = "neuralmind/bert-base-portuguese-cased"

@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)

def generate_embedding(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()
```

O modelo é cacheado em memória — não instancie por request.

---

## 6. Docker Compose

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/pdf_extractor
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
    depends_on: [db, redis, qdrant]

  worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/pdf_extractor
      - REDIS_URL=redis://redis:6379/0
    depends_on: [db, redis, qdrant]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: pdf_extractor
      POSTGRES_PASSWORD: postgres
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  qdrant:
    image: qdrant/qdrant:latest
    volumes: [qdrant_data:/qdrant/storage]

volumes:
  postgres_data:
  qdrant_data:
```

```dockerfile
# Dockerfile — multi-stage
FROM python:3.12-slim AS base
RUN pip install uv

FROM base AS deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM deps AS app
COPY src/ ./src/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
