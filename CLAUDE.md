# PDF Extractor — CLAUDE.md

Pipeline assíncrono de extração estruturada de dados de relatórios governamentais em PDF. Combina parser determinístico (pdfplumber + camelot) com LLM (Claude API) via few-shot dinâmico armazenado no Qdrant. Aprende continuamente com Corrections humanas sem reprocessamento.

---

## Documentação essencial

| Arquivo | Conteúdo |
|---|---|
| `CONTEXT.md` | Glossário canônico — **fonte da verdade para nomenclatura** |
| `docs/PRD.md` | Problem statement, user stories, decisões de implementação |
| `docs/ARCHITECTURE.md` | Diagramas Mermaid do sistema (manter atualizado com `/update-docs`) |
| `docs/specs/api.md` | Endpoints da API |
| `docs/specs/components.md` | Componentes e responsabilidades |
| `docs/specs/data-model.md` | Tabelas PostgreSQL + coleções Qdrant |
| `docs/adr/` | Decisões arquiteturais com justificativa |

---

## Skills — quando usar cada um

### Ao escrever ou revisar qualquer código Python
`/implementation-contract` — enforça termos do `CONTEXT.md`, naming conventions, type hints, single responsibility, custom exceptions. Disparar proativamente ao ver sinônimos ou violações.

### Ao escrever testes
`/testing-contract` — estratégia por componente (unit vs integration), fixtures reais de PostgreSQL e Qdrant, como mockar Claude API e Celery.

### Ao implementar endpoints, queries SQLAlchemy, tasks Celery, buscas Qdrant ou embeddings
`/python-stack-patterns` — padrões específicos do stack: FastAPI dependency injection, SQLAlchemy 2.0 async, Celery task config, Qdrant client async, sentence-transformers com `lru_cache`.

### Ao implementar o `LLMExtractor` ou qualquer código que importe `anthropic`
`/claude-api` — Anthropic SDK patterns: prompt caching (prefixo estável = schema + contexto + few-shot), streaming, batch API, retry para rate limit, model selection. Apps neste projeto devem usar prompt caching.

### Ao implementar `FewShotRetriever` ou `DomainClassifier` (Qdrant)
`/rag-qdrant` — payload indexing por `domain_id` (obrigatório para performance de busca filtrada), quantização para produção, gRPC client, advanced filtered search.

### Ao lidar com concorrência async no pipeline (Celery + asyncio + SQLAlchemy async)
`/async-python-patterns` — `asyncio.run()` dentro de tasks Celery, timeouts coordenados no pipeline, `gather()` para paralelizar etapas independentes.

### Ao receber um PDF de Domínio desconhecido (cold start)
`/register-domain` — analisa o PDF, propõe Domain Registration (organ, context, sections, known_fields, periodicity) para confirmação do admin.

### Ao ajustar qualidade de extração de um Domínio
`/build-extraction-prompt` — ajuste fino do prompt sem tocar no código: estrutura, instrução de `null` para campos ausentes, posição dos few-shot examples.

### Ao analisar Corrections acumuladas e evoluir o Schema
`/evolve-schema` — sugere campos a adicionar/deprecar, avalia se Schema está pronto para `validated` (critério: ≥10 jobs validados, <2 corrections/job, nenhum campo novo recente).

### Após qualquer mudança de componente, endpoint ou data model
`/update-docs` — regenera `docs/ARCHITECTURE.md` com diagramas Mermaid atualizados.

---

## Convenções críticas

- **Nomenclatura**: use sempre os termos exatos do `CONTEXT.md`. Se o `CONTEXT.md` diz `Extraction Job`, o código diz `extraction_job` — nunca `task`, `process`, `request`.
- **Módulos**: um componente de `docs/specs/components.md` = um arquivo em `src/`. Sem lógica de negócio no orchestrator, API layer ou UI.
- **Schema imutável por job**: cada `ExtractionJob` registra a `SchemaVersion` ativa no momento. Reprocessamento é sempre explícito e manual.
- **Banco real nos testes**: não mockar PostgreSQL — usar instância de teste. Qdrant pode ser mockado.
- **Prompt caching**: toda chamada ao Claude API que repete schema + contexto + few-shot deve usar `cache_control`. Verificar `usage.cache_read_input_tokens` > 0.
- **Payload index**: antes de qualquer busca filtrada no Qdrant por `domain_id`, garantir que `create_payload_index` foi criado para esse campo.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API + Frontend | FastAPI + HTMX + Jinja2 |
| Job Queue | Celery + Redis |
| Banco de dados | PostgreSQL + SQLAlchemy 2.0 async + Alembic |
| Vector store | Qdrant (AsyncQdrantClient) |
| Embeddings | sentence-transformers `neuralmind/bert-base-portuguese-cased` |
| PDF determinístico | pdfplumber + camelot |
| LLM | Claude API (Anthropic SDK Python) |
| Infra local | Docker Compose |
| Tooling | uv, ruff, mypy, pytest + pytest-asyncio |
