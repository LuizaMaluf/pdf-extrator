from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.settings import settings


class FewShotExample(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: UUID
    domain_id: UUID
    schema_version: int
    extraction: dict[str, object]
    score: float = Field(ge=0.0, le=1.0)


class FewShotRetriever:
    async def retrieve(self, pdf_text: str, domain_id: UUID) -> list[FewShotExample]:
        raise NotImplementedError
