import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch

from app.database import Base
from app.main import app

DATABASE_URL_TEST = "postgresql+asyncpg://postgres:postgres@localhost:5432/pdf_extractor_test"


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
        await session.rollback()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_claude_api():
    with patch("app.llm_extractor.anthropic.Anthropic") as mock:
        mock.return_value.messages.create = AsyncMock(
            return_value=_mock_claude_response()
        )
        yield mock


@pytest.fixture
def mock_qdrant():
    with patch("app.vector_store.get_qdrant_client") as mock:
        client = AsyncMock()
        client.search = AsyncMock(return_value=[])
        client.upsert = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_celery():
    with patch("app.tasks.process_extraction_job.delay") as mock:
        yield mock


def _mock_claude_response() -> object:
    from unittest.mock import MagicMock

    response = MagicMock()
    response.content = [MagicMock(text='{"fields": {}}')]
    return response
