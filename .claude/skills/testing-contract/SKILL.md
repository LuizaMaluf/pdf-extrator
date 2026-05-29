---
name: testing-contract
description: Use this skill whenever writing tests for this project. Defines how to test each component in isolation, what to test vs skip, pytest-asyncio setup, real PostgreSQL/Qdrant test fixtures, and how to mock the Claude API and Celery. Trigger on: "write tests for", "how do I test", "add a test", "TDD", "red-green-refactor", or any time a test file is being created or reviewed.
---

# Testing Contract

Guia de escrita de testes para o PDF Extractor. Cada componente tem uma estratégia de teste específica — consulte a seção do componente que você está testando.

---

## Filosofia

**Teste comportamento externo, não implementação interna.** Um bom teste verifica o que entra e o que sai de um componente através de sua interface pública. Se você precisa inspecionar o estado interno ou verificar qual método privado foi chamado, está testando a implementação — e esse teste vai quebrar em refatorações sem motivo.

**Vertical slices** — um teste por vez, não todos de uma vez. Escreva um teste, faça passar, escreva o próximo. Testes escritos em bloco antes da implementação testam o formato imaginado, não o comportamento real.

**Não mocke o banco de dados** — use um PostgreSQL real de teste. O schema muda, as migrations evoluem, e testes com mock de banco não pegam nada disso.

---

## Setup

### pyproject.toml

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.pytest.ini_options.markers]
integration = "testes que precisam de serviços externos (DB, Qdrant)"
unit = "testes sem dependências externas"
```

### conftest.py

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app
from app.database import Base

DATABASE_URL_TEST = "postgresql+asyncpg://postgres:postgres@localhost:5432/pdf_extractor_test"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(DATABASE_URL_TEST)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # desfaz cada teste para isolamento

@pytest_asyncio.fixture
async def api_client(db_session) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

@pytest.fixture
def mock_claude_api():
    with patch("app.llm_extractor.anthropic.Anthropic") as mock:
        mock.return_value.messages.create = AsyncMock(return_value=_mock_claude_response())
        yield mock

@pytest.fixture
def mock_qdrant():
    with patch("app.vector_store.qdrant_client") as mock:
        mock.search = AsyncMock(return_value=[])
        mock.upsert = AsyncMock()
        yield mock
```

---

## Como testar cada componente

### DomainClassifier

Testa os três caminhos: `domain_id` fornecido, confidence alta, confidence baixa.

```python
# tests/test_domain_classifier.py
import pytest
from unittest.mock import AsyncMock, patch
from app.domain_classifier import DomainClassifier
from app.schemas import ClassificationResult

@pytest.mark.asyncio
async def test_classify_with_explicit_domain_id_returns_full_confidence():
    classifier = DomainClassifier()
    result = await classifier.classify(text="qualquer texto", domain_id=some_uuid)
    assert result.domain_id == some_uuid
    assert result.confidence == 1.0

@pytest.mark.asyncio
async def test_classify_high_confidence_returns_domain(mock_qdrant):
    mock_qdrant.search.return_value = [_mock_hit(score=0.92, domain_id=known_domain_id)]
    classifier = DomainClassifier()
    result = await classifier.classify(text="relatório execução orçamentária")
    assert result.domain_id == known_domain_id
    assert result.confidence >= CONFIDENCE_THRESHOLD

@pytest.mark.asyncio
async def test_classify_low_confidence_raises_or_flags(mock_qdrant):
    mock_qdrant.search.return_value = [_mock_hit(score=0.60, domain_id=known_domain_id)]
    classifier = DomainClassifier()
    result = await classifier.classify(text="texto ambíguo")
    assert result.confidence < CONFIDENCE_THRESHOLD
    # verificar que o status do job muda para needs_confirmation em integração
```

### ExtractionPromptBuilder

Módulo puro — não precisa de fixtures, não precisa de mocks.

```python
# tests/test_extraction_prompt_builder.py
from app.extraction_prompt_builder import build_extraction_prompt
from tests.factories import make_schema, make_domain_context, make_few_shot_example

def test_prompt_contains_all_active_schema_fields():
    schema = make_schema(fields=["total_despesas", "percentual_executado"])
    prompt = build_extraction_prompt(schema, make_domain_context(), [], "texto qualquer")
    assert "total_despesas" in prompt
    assert "percentual_executado" in prompt

def test_prompt_excludes_deprecated_fields():
    schema = make_schema(active=["valor_empenhado"], deprecated=["codigo_antigo"])
    prompt = build_extraction_prompt(schema, make_domain_context(), [], "texto")
    assert "valor_empenhado" in prompt
    assert "codigo_antigo" not in prompt

def test_prompt_includes_few_shot_examples():
    examples = [make_few_shot_example(fields={"valor_total": 1000.0})]
    prompt = build_extraction_prompt(make_schema(), make_domain_context(), examples, "texto")
    assert "valor_total" in prompt
    assert "1000.0" in prompt

def test_prompt_instructs_null_for_missing_fields():
    prompt = build_extraction_prompt(make_schema(), make_domain_context(), [], "")
    assert "null" in prompt.lower()
    assert "não invente" in prompt.lower() or "never" in prompt.lower()
```

### SchemaRegistry

Requer PostgreSQL real. Testa o ciclo de vida completo.

```python
# tests/test_schema_registry.py
import pytest
from app.schema_registry import SchemaRegistry
from app.schemas import SchemaStatus

@pytest.mark.asyncio
@pytest.mark.integration
async def test_schema_starts_as_draft(db_session, created_domain):
    registry = SchemaRegistry(db_session)
    schema = await registry.get_active(created_domain.id)
    assert schema.status == SchemaStatus.DRAFT
    assert schema.version == 1

@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_field_creates_new_version(db_session, created_domain):
    registry = SchemaRegistry(db_session)
    new_field = SchemaField(name="novo_campo", field_type=FieldType.NUMBER)
    updated = await registry.add_field(created_domain.id, new_field)
    assert updated.version == 2
    assert any(f.name == "novo_campo" for f in updated.fields)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_validated_schema_cannot_remove_fields(db_session, validated_domain):
    registry = SchemaRegistry(db_session)
    with pytest.raises(SchemaValidationError):
        await registry.deprecate_all_fields(validated_domain.id)  # operação inválida

@pytest.mark.asyncio
@pytest.mark.integration
async def test_previous_version_is_immutable(db_session, created_domain):
    registry = SchemaRegistry(db_session)
    v1 = await registry.get_version(created_domain.id, version=1)
    await registry.add_field(created_domain.id, SchemaField(name="campo_novo"))
    v1_again = await registry.get_version(created_domain.id, version=1)
    assert v1.fields == v1_again.fields  # v1 não mudou
```

### CorrectionProcessor

Testa persistência no PostgreSQL E upsert no Qdrant E evolução de schema.

```python
# tests/test_correction_processor.py
@pytest.mark.asyncio
@pytest.mark.integration
async def test_correction_persists_to_db(db_session, mock_qdrant, completed_job):
    processor = CorrectionProcessor(db_session)
    corrections = [Correction(field_name="valor_total", corrected_value=5000.0)]
    await processor.process(completed_job.id, corrections, new_fields=[])

    saved = await db_session.get(CorrectionModel, ...)
    assert saved.corrected_value == 5000.0

@pytest.mark.asyncio
@pytest.mark.integration
async def test_correction_upserts_few_shot_to_qdrant(db_session, mock_qdrant, completed_job):
    processor = CorrectionProcessor(db_session)
    await processor.process(completed_job.id, [some_correction], new_fields=[])
    mock_qdrant.upsert.assert_called_once()
    call_args = mock_qdrant.upsert.call_args
    assert call_args.kwargs["collection_name"] == "few_shot_examples"

@pytest.mark.asyncio
@pytest.mark.integration
async def test_new_field_evolves_schema(db_session, mock_qdrant, completed_job):
    processor = CorrectionProcessor(db_session)
    new_field = NewField(name="campo_descoberto", value=42, field_type=FieldType.NUMBER)
    await processor.process(completed_job.id, [], new_fields=[new_field])

    schema = await SchemaRegistry(db_session).get_active(completed_job.domain_id)
    assert any(f.name == "campo_descoberto" for f in schema.fields)
```

### API Layer

Testa enforcement de roles e contratos de response — sem lógica de negócio.

```python
# tests/test_api_jobs.py
@pytest.mark.asyncio
async def test_upload_pdf_returns_job_id(api_client, analyst_token, mock_celery):
    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert response.status_code == 202
    assert "job_id" in response.json()
    assert response.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_post_domains_requires_admin_role(api_client, analyst_token):
    response = await api_client.post(
        "/api/v1/domains",
        json={...},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_job_returns_correct_status(api_client, analyst_token, completed_job):
    response = await api_client.get(
        f"/api/v1/jobs/{completed_job.id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
```

---

## O que não testar

- **Implementação interna de componentes** — se renomear um método privado quebrar um teste, o teste está errado
- **ORM em si** (se `session.execute()` funciona) — confie no SQLAlchemy
- **Serialização do Qdrant** — confie na lib
- **Lógica interna do Celery** — teste o resultado no banco, não se a task foi chamada
- **Todos os edge cases hipotéticos** — teste os caminhos críticos e os erros que realmente podem acontecer

---

## Factories para fixtures

Centralize criação de objetos de teste em `tests/factories.py` para evitar repetição.

```python
# tests/factories.py
from app.schemas import Schema, SchemaField, FieldType, SchemaStatus
import uuid

def make_schema(
    domain_id: uuid.UUID | None = None,
    active: list[str] | None = None,
    deprecated: list[str] | None = None,
    status: SchemaStatus = SchemaStatus.DRAFT,
) -> Schema:
    fields = [
        SchemaField(name=n, field_type=FieldType.STRING, status="active")
        for n in (active or ["campo_padrao"])
    ] + [
        SchemaField(name=n, field_type=FieldType.STRING, status="deprecated")
        for n in (deprecated or [])
    ]
    return Schema(
        id=uuid.uuid4(),
        domain_id=domain_id or uuid.uuid4(),
        version=1,
        status=status,
        fields=fields,
    )
```
