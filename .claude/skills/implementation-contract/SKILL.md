---
name: implementation-contract
description: Use this skill whenever writing new code or reviewing existing code in this project. Enforces naming conventions, clean code principles, domain term consistency (from CONTEXT.md), and module design contracts. Trigger on: "review this code", "does this follow our standards?", "write a function for X", "check the naming", "implement X", or any time new Python code is being written or reviewed for this project. Also trigger proactively when you notice code that violates these contracts — don't wait to be asked.
---

# Implementation Contract

Guia de escrita e revisão de código para o PDF Extractor. Toda implementação deve seguir esses contratos — tanto ao escrever código novo quanto ao revisar código existente.

---

## 1. Domain Term Enforcement

O glossário em `CONTEXT.md` é a fonte da verdade para nomenclatura. Nomes no código devem espelhar os termos do domínio exatamente — nunca use sinônimos.

| Use | Never |
|---|---|
| `domain` | `ministry`, `source`, `category` |
| `extractor` | `parser`, `reader`, `processor` |
| `schema` | `template`, `structure`, `model` |
| `extraction_job` | `task`, `process`, `request` |
| `correction` | `fix`, `edit`, `adjustment` |
| `few_shot_example` | `training_sample`, `example` |
| `confidence` | `score`, `probability`, `certainty` |
| `domain_registration` | `setup`, `config`, `cadastro` |
| `schema_version` | `version`, `snapshot` |
| `validation` | `review`, `approval`, `audit` |

When reading code: if you find a synonym, rename it. When writing code: look up the term in `CONTEXT.md` first.

---

## 2. Naming Conventions

### Functions and methods
Use verb phrases that say what the function **does**, not what it is.

```python
# Good
def classify_domain(text: str) -> ClassificationResult: ...
def retrieve_few_shot_examples(pdf_text: str, domain_id: UUID) -> list[FewShotExample]: ...
def build_extraction_prompt(schema: Schema, context: DomainContext, examples: list[FewShotExample]) -> str: ...

# Bad
def domain_classification(text): ...  # noun phrase
def process(text): ...                 # too vague
def run(pdf, domain): ...              # says nothing
```

### Boolean functions and variables
Prefix with `is_`, `has_`, `can_`.

```python
is_confidence_sufficient(confidence: float) -> bool
has_active_schema(domain_id: UUID) -> bool
can_analyst_access(role: Role, resource: str) -> bool

is_validated = schema.status == SchemaStatus.VALIDATED
has_few_shot_examples = len(examples) > 0
```

### Classes
Use nouns that map directly to domain concepts from `CONTEXT.md`.

```python
# Good — mirrors CONTEXT.md terms exactly
class DomainClassifier: ...
class SchemaRegistry: ...
class CorrectionProcessor: ...
class FewShotRetriever: ...
class ExtractionOrchestrator: ...

# Bad
class PDFHandler: ...      # too generic
class DataProcessor: ...   # says nothing
class Manager: ...         # anti-pattern
```

### Variables
Full words, no abbreviations except universally understood ones (`i`, `e`, `df`).

```python
# Good
extraction_result = extractor.run(pdf_path, domain)
schema_version = registry.get_active_version(domain_id)
few_shot_examples = retriever.retrieve(pdf_text, domain_id)

# Bad
res = extractor.run(pdf, d)
sv = registry.get_active(did)
examples = retriever.retrieve(t, id)
```

### Constants and enums
`SCREAMING_SNAKE_CASE` for constants. Enums as classes with descriptive member names.

```python
CONFIDENCE_THRESHOLD = 0.85
MAX_FEW_SHOT_EXAMPLES = 5
MIN_FEW_SHOT_SCORE = 0.6

class ExtractionJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    NEEDS_CONFIRMATION = "needs_confirmation"
    NEEDS_REGISTRATION = "needs_registration"
    COMPLETED = "completed"
    VALIDATED = "validated"
    FAILED = "failed"

class SchemaStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
```

### Private methods
Prefix with `_`. Private = implementation detail, not part of the module's interface.

```python
class DomainClassifier:
    def classify(self, text: str) -> ClassificationResult: ...     # public interface
    def _embed_text(self, text: str) -> list[float]: ...           # internal detail
    def _search_signatures(self, embedding: list[float]) -> ...:   # internal detail
```

---

## 3. Function Design

### Single responsibility
Each function does one thing. If you need "and" to describe what a function does, split it.

```python
# Bad: two responsibilities
def extract_and_save(pdf_path: str, domain: Domain) -> None:
    result = extractor.run(pdf_path, domain)
    db.save(result)

# Good: separated
def extract(pdf_path: str, domain: Domain) -> ExtractionResult:
    return extractor.run(pdf_path, domain)

def save_extraction_result(result: ExtractionResult, job_id: UUID) -> None:
    db.save(result, job_id)
```

### Size guideline
Functions longer than ~20 lines are a signal to look for extraction opportunities — not a hard rule, but a useful alarm. Long functions usually hide multiple responsibilities.

### Early returns over nesting
Prefer guard clauses that return early. Deep nesting makes conditions hard to follow.

```python
# Bad: nested
def process_correction(correction: Correction) -> None:
    if correction.is_valid():
        if correction.is_new_field():
            schema_registry.add_field(correction.field)
            qdrant.upsert(correction)
        else:
            qdrant.upsert(correction)

# Good: early return
def process_correction(correction: Correction) -> None:
    if not correction.is_valid():
        return

    if correction.is_new_field():
        schema_registry.add_field(correction.field)

    qdrant.upsert(correction)
```

### No magic numbers or strings
Any literal with business meaning becomes a named constant.

```python
# Bad
if confidence < 0.85:
    ...
examples = retriever.retrieve(text, domain_id, limit=5)

# Good
if confidence < CONFIDENCE_THRESHOLD:
    ...
examples = retriever.retrieve(text, domain_id, limit=MAX_FEW_SHOT_EXAMPLES)
```

---

## 4. Type Hints e Pydantic V2

All function signatures must have complete type hints — parameters and return type. No exceptions.

Use Python 3.12+ syntax — sem imports de `typing` para os casos comuns:

```python
# Python 3.12+ — use esta forma
def classify_domain(text: str, domain_id: UUID | None = None) -> ClassificationResult: ...
def retrieve_examples(domain_id: UUID) -> list[FewShotExample]: ...
def get_job(job_id: UUID) -> ExtractionJob | None: ...

# Não use — forma legada
from typing import Optional, List, Dict
def classify_domain(text: str, domain_id: Optional[UUID] = None) -> ClassificationResult: ...
def retrieve_examples(domain_id: UUID) -> List[FewShotExample]: ...
```

Use domain types (Pydantic V2 models) em vez de `dict` quando o shape é conhecido.

```python
# Bad: opaque
def build_prompt(schema: dict, examples: list) -> str: ...

# Good: explicit
def build_prompt(schema: Schema, examples: list[FewShotExample], context: DomainContext) -> str: ...
```

### Pydantic V2 — modelos de domínio

```python
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class FewShotExample(BaseModel):
    model_config = ConfigDict(frozen=True)  # imutável após criação

    job_id: UUID
    domain_id: UUID
    schema_version: int
    extraction: dict[str, object]
    score: float = Field(ge=0.0, le=1.0)

class KnownField(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-z_]+$")  # snake_case obrigatório
    description: str = Field(min_length=5)
```

Regras Pydantic V2:
- `model_config = ConfigDict(...)` em vez de `class Config`
- `from_attributes=True` para converter modelos ORM
- `frozen=True` para objetos que não devem mudar após criação
- Validators com `@field_validator` em vez de `@validator`

---

## 5. Module Design

Each component from `docs/specs/components.md` maps to exactly one module. No component logic bleeds into another module.

```
src/
  domain_classifier.py     ← DomainClassifier only
  deterministic_extractor.py
  few_shot_retriever.py
  extraction_prompt_builder.py
  llm_extractor.py
  extraction_orchestrator.py  ← coordinates; no business logic
  schema_registry.py
  correction_processor.py
  domain_registration_handler.py
  api/                     ← routing only; no business logic
  ui/                      ← templates and HTMX handlers
```

The orchestrator and API layer **coordinate** — they must not contain business logic. If you find yourself writing a conditional in a Celery task or a FastAPI route that belongs in a domain component, extract it.

---

## 6. Error Handling

Use custom exceptions per domain concept. No bare `except`. Never swallow errors silently.

```python
# Define domain exceptions
class DomainNotFoundError(Exception): ...
class LowConfidenceError(Exception):
    def __init__(self, confidence: float, threshold: float):
        self.confidence = confidence
        self.threshold = threshold

class SchemaValidationError(Exception): ...
class ExtractionFailedError(Exception): ...

# Use them explicitly
def classify_domain(text: str) -> ClassificationResult:
    result = qdrant.search(...)
    if result.confidence < CONFIDENCE_THRESHOLD:
        raise LowConfidenceError(result.confidence, CONFIDENCE_THRESHOLD)
    return result

# Never
try:
    classify_domain(text)
except:          # catches everything including KeyboardInterrupt
    pass         # swallows the error
```

---

## 7. Doing a Code Review

When reviewing code, check in this order:

1. **Domain terms** — do names match `CONTEXT.md` exactly? Flag any synonym.
2. **Function names** — verb phrases? Clear intent? No vague names (`process`, `handle`, `run`)?
3. **Single responsibility** — does each function do one thing? Any "and" in the description?
4. **Type hints** — all signatures complete?
5. **Magic values** — any hardcoded numbers or strings with business meaning?
6. **Early returns** — any deep nesting that a guard clause would flatten?
7. **Module boundaries** — any business logic in orchestrator, API, or UI layer?
8. **Error handling** — custom exceptions? No bare `except`?

Report findings grouped by file, with the specific line and a concrete fix. Don't just flag — propose the corrected name or refactored function.

---

## 8. Writing New Code

Before writing, answer these:

- What domain term from `CONTEXT.md` does this belong to?
- What is the single responsibility of this function/class?
- What are the input and output types?
- What can go wrong, and which custom exception should I raise?

Then write the signature first — if the signature is clear, the body usually follows naturally.
