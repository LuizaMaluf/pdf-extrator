from pydantic import BaseModel, ConfigDict


class LLMExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    fields: dict[str, object]
    source: str = "llm"


class LLMExtractor:
    async def extract(self, prompt: str) -> LLMExtractionResult:
        raise NotImplementedError
