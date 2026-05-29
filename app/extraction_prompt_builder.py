from app.few_shot_retriever import FewShotExample


class Schema:
    """Placeholder — substituído pelo modelo ORM/Pydantic na implementação."""
    fields: list[object]
    status: str


class DomainContext:
    """Placeholder — substituído pelo modelo ORM/Pydantic na implementação."""
    organ: str
    context: str
    priority_sections: list[str]
    known_fields: list[dict[str, str]]


def build_extraction_prompt(
    schema: object,
    context: object,
    examples: list[FewShotExample],
    remaining_text: str,
) -> str:
    raise NotImplementedError
