from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.settings import settings


class ClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain_id: UUID
    confidence: float = Field(ge=0.0, le=1.0)


class DomainClassifier:
    async def classify(self, text: str, domain_id: UUID | None = None) -> ClassificationResult:
        raise NotImplementedError
