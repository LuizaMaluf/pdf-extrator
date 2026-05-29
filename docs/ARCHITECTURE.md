# Arquitetura — PDF Extractor

> Última atualização: 2026-05-28

## Stack

| Camada | Tecnologia |
|---|---|
| API + Frontend | FastAPI + HTMX + Jinja2 |
| Job Queue | Celery + Redis |
| Banco de dados | PostgreSQL + SQLAlchemy + Alembic |
| Vector store | Qdrant |
| Embeddings | sentence-transformers (`neuralmind/bert-base-portuguese-cased`) |
| PDF determinístico | pdfplumber + camelot |
| LLM | Claude API (Anthropic SDK) |
| Infraestrutura | Docker Compose |

---

## Visão Geral

```mermaid
graph TB
    subgraph API ["FastAPI"]
        UP[POST /pdfs]
        JOB[GET /jobs/:id]
        VAL[PATCH /jobs/:id/validation]
        DOM[POST /domains]
        QRY[GET /domains/:id/extractions]
    end

    subgraph Queue ["Celery + Redis"]
        CW[Extraction Worker]
    end

    subgraph Pipeline ["Pipeline de Extração"]
        DC[Domain Classifier]
        DET[Parser Determinístico\npdfplumber + camelot]
        LLM[LLM\nClaude API]
        FSR[Few-Shot Retriever]
    end

    subgraph Storage ["Storage"]
        PG[(PostgreSQL)]
        QD[(Qdrant)]
        FS[/Filesystem\nPDFs/]
    end

    subgraph UI ["Interface de Validação"]
        HTMX[HTMX + Jinja2]
    end

    UP --> FS
    UP --> CW
    CW --> DC
    DC --> DET
    DET --> FSR
    FSR --> QD
    FSR --> LLM
    LLM --> PG
    VAL --> PG
    VAL --> QD
    QRY --> PG
    DOM --> PG
    HTMX --> VAL
    HTMX --> JOB
```

O upload de um PDF dispara um Extraction Job assíncrono no Celery. O Domain Classifier identifica o tipo de relatório e aciona o Extractor híbrido: o parser determinístico cobre campos estruturados, e o LLM (Claude API) cobre o restante usando Few-Shot Examples recuperados do Qdrant por similaridade semântica. O resultado fica disponível para Validation via interface HTMX, e as Corrections alimentam de volta o Qdrant e evoluem o Schema no PostgreSQL.

---

## Fluxo de Extração

```mermaid
sequenceDiagram
    actor U as Usuário
    participant API as FastAPI
    participant Q as Celery
    participant DC as Domain Classifier
    participant EXT as Extractor
    participant FSR as Few-Shot Retriever
    participant LLM as Claude API
    participant DB as PostgreSQL
    participant VEC as Qdrant

    U->>API: POST /pdfs (arquivo + domain_id?)
    API->>DB: cria Extraction Job (pending)
    API-->>U: job_id

    API->>Q: enfileira job

    Q->>DC: classifica Domínio
    alt domain_id fornecido
        DC-->>Q: confidence 1.0
    else classificação automática
        DC->>VEC: busca domain_signatures
        VEC-->>DC: domínio + confidence
        alt confidence >= 0.85
            DC-->>Q: domínio confirmado
        else confidence < 0.85
            DC->>DB: status → needs_confirmation
            U->>API: POST /jobs/:id/confirm-domain
            API->>Q: reenfileira com domain_id
        end
    end

    Q->>EXT: extrai (fase 1 — determinístico)
    EXT-->>Q: campos estruturados

    Q->>FSR: recupera exemplos similares
    FSR->>VEC: busca few_shot_examples (filtro domain_id)
    VEC-->>FSR: top-5 exemplos
    FSR-->>Q: few-shot examples

    Q->>LLM: prompt (schema + contexto + few-shot + texto restante)
    LLM-->>Q: campos extraídos

    Q->>DB: salva resultado, status → completed

    U->>API: GET /jobs/:id (polling)
    API-->>U: status: completed + result
```

Disparado por um upload via `POST /pdfs`. A decisão central é a classificação de Domínio: se a Confidence for alta, o pipeline segue automaticamente; se baixa, o humano confirma antes de prosseguir. O fluxo termina com sucesso quando o job atinge status `completed` e o resultado está disponível para Validation.

---

## Cold Start — Novo Domínio

```mermaid
sequenceDiagram
    actor A as Admin
    actor U as Usuário
    participant API as FastAPI
    participant Q as Celery
    participant DB as PostgreSQL
    participant VEC as Qdrant

    U->>API: POST /pdfs (PDF desconhecido)
    API->>Q: enfileira job
    Q->>DB: status → needs_registration

    Note over A: /register-domain skill ativado
    A->>A: lê PDF, infere campos
    A->>API: POST /domains\n(organ, context, sections, known_fields, periodicity)
    API->>DB: cria Domain + Schema v1 (draft)
    API->>VEC: indexa domain_signature
    API-->>A: domain_id

    A->>API: POST /jobs/:id/confirm-domain
    API->>Q: reenfileira job com domain_id

    Q->>Q: extrai sem Few-Shot Examples\n(cold start — usa apenas context + known_fields)
    Q->>DB: status → completed

    U->>API: GET /jobs/:id/validation
    U->>API: PATCH /jobs/:id/validation (corrections)
    API->>DB: salva Corrections
    API->>VEC: indexa primeiro Few-Shot Example
    API->>DB: Schema v1 evolui se new_fields
```

Ativado quando o Domínio de um PDF não é reconhecido. O admin executa o skill `/register-domain`, que analisa o PDF e propõe os campos do Domain Registration para confirmação. A primeira extração roda sem Few-Shot Examples — usa apenas o contexto registrado. A primeira Validation cria o primeiro Few-Shot Example e esboça o Schema `draft`.

---

## Ciclo de Vida do Schema

```mermaid
stateDiagram-v2
    [*] --> draft : Domain Registration\ncria Schema v1

    draft --> draft : Correction com new_fields\n(nova Schema Version)
    draft --> validated : Admin declara validated\n(POST /domains/:id/schema/validate)

    validated --> validated : Correction com new_fields\n(nova Schema Version, campos só crescem)

    state validated {
        [*] --> active
        active --> deprecated : campo obsoleto\n(nunca removido)
    }
```

O Schema emerge das primeiras extrações de um Domínio e é declarado `validated` explicitamente pelo admin quando está maduro (critério: ≥10 jobs validados, <2 corrections/job, nenhum campo novo recente). Depois de `validated`, campos só são acrescidos — nunca removidos, apenas marcados `deprecated`. Cada mudança de campo cria uma nova Schema Version imutável, e cada Extraction Job fica vinculado à versão ativa no momento de sua execução.

---

## Modelo de Dados

```mermaid
erDiagram
    users {
        uuid id PK
        varchar username
        enum role
    }

    domains {
        uuid id PK
        varchar name
        varchar organ
        text context
        enum periodicity
    }

    schema_versions {
        uuid id PK
        uuid domain_id FK
        int version
        enum status
    }

    schema_fields {
        uuid id PK
        uuid domain_id FK
        varchar name
        enum field_type
        enum status
        int added_in_version
    }

    extraction_jobs {
        uuid id PK
        uuid domain_id FK
        uuid schema_version_id FK
        enum status
        float confidence
        jsonb result
    }

    corrections {
        uuid id PK
        uuid job_id FK
        varchar field_name
        jsonb original_value
        jsonb corrected_value
        bool is_new_field
    }

    domains ||--o{ schema_versions : "tem"
    domains ||--o{ schema_fields : "define"
    domains ||--o{ extraction_jobs : "classifica"
    schema_versions ||--o{ extraction_jobs : "vincula"
    extraction_jobs ||--o{ corrections : "recebe"
    users ||--o{ extraction_jobs : "cria"
    users ||--o{ corrections : "faz"
```

PostgreSQL armazena todos os dados estruturados: usuários, domínios, schemas versionados, jobs e correções. Qdrant mantém duas coleções vetoriais: `domain_signatures` (usada pelo Domain Classifier para identificar novos PDFs) e `few_shot_examples` (usada pelo Few-Shot Retriever para recuperar exemplos por similaridade semântica filtrada por Domínio). PDFs brutos ficam no filesystem local.

---

## Decisões Arquiteturais

| ADR | Decisão | Motivação |
|---|---|---|
| [0001](adr/0001-qdrant-vector-store.md) | Qdrant como vector store | Filtragem por Domínio nativa; pgvector degrada com volume |
| [0002](adr/0002-sentence-transformers-portugues.md) | sentence-transformers PT-BR | Jargão técnico governamental brasileiro; sem custo por chamada |
| [0003](adr/0003-celery-redis-job-queue.md) | Celery + Redis para jobs | Suporte nativo a retries, prioridades e task chaining |
