from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExtractedField(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: object
    source: str = "deterministic"


class DeterministicExtractor:
    def extract(self, pdf_path: Path, domain_id: UUID) -> list[ExtractedField]:
        raise NotImplementedError
