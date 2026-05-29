import uuid

from app.few_shot_retriever import FewShotExample
from app.models.schema_field import FieldStatus, FieldType, SchemaField
from app.models.schema_version import SchemaStatus


def make_schema_field(
    name: str = "campo_padrao",
    field_type: FieldType = FieldType.STRING,
    status: FieldStatus = FieldStatus.ACTIVE,
    added_in_version: int = 1,
    domain_id: uuid.UUID | None = None,
) -> SchemaField:
    field = SchemaField()
    field.id = uuid.uuid4()
    field.domain_id = domain_id or uuid.uuid4()
    field.name = name
    field.field_type = field_type
    field.status = status
    field.added_in_version = added_in_version
    return field


def make_few_shot_example(
    domain_id: uuid.UUID | None = None,
    fields: dict[str, object] | None = None,
    score: float = 0.85,
) -> FewShotExample:
    return FewShotExample(
        job_id=uuid.uuid4(),
        domain_id=domain_id or uuid.uuid4(),
        schema_version=1,
        extraction=fields or {"campo_padrao": "valor"},
        score=score,
    )
