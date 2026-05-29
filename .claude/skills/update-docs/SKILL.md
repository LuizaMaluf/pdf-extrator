---
name: update-docs
description: Use this skill to generate or update the living architecture documentation at docs/ARCHITECTURE.md. Run whenever components, endpoints, data models, or flows change. Reads the current state of specs/, CONTEXT.md, ADRs, and source code to regenerate Mermaid diagrams and flow descriptions that reflect the project as it actually is.
---

# Update Living Documentation

Regenera `docs/ARCHITECTURE.md` com diagramas Mermaid e descrições de fluxo refletindo o estado atual do projeto.

---

## Quando executar este skill

- Após adicionar ou remover um endpoint
- Após criar ou modificar um componente
- Após uma mudança no data model
- Após uma nova decisão arquitetural (ADR)
- Antes de um code review ou onboarding de novo membro

---

## Passo 1 — Ler o estado atual do projeto

Antes de escrever qualquer coisa, leia:

```
CONTEXT.md                        → glossário e termos canônicos
docs/specs/api.md                 → endpoints atuais
docs/specs/components.md          → componentes e responsabilidades
docs/specs/data-model.md          → tabelas e coleções
docs/adr/                         → decisões arquiteturais
src/                              → estrutura real do código (se existir)
```

Se o código divergir dos specs, **o código é a fonte da verdade**. Atualize o diagrama para refletir o que o código faz, e anote a divergência como um comentário no ARCHITECTURE.md para revisão posterior.

---

## Passo 2 — Gerar os diagramas

Escreva ou atualize cada diagrama abaixo. Use os **termos exatos do CONTEXT.md** — nunca sinônimos.

### Diagrama 1 — Visão geral do sistema

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

### Diagrama 2 — Fluxo principal de extração

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

### Diagrama 3 — Cold start (novo Domínio)

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

### Diagrama 4 — Ciclo de vida do Schema

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

### Diagrama 5 — Modelo de dados (simplificado)

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

---

## Passo 3 — Escrever as descrições de fluxo

Para cada fluxo, escreva um parágrafo curto **abaixo do diagrama** explicando:
- O que dispara o fluxo
- A decisão mais importante no meio do caminho
- O que indica que terminou com sucesso

Use os termos do CONTEXT.md. Sem jargão técnico desnecessário.

---

## Passo 4 — Montar o ARCHITECTURE.md

Estrutura do arquivo final:

```markdown
# Arquitetura — PDF Extractor

> Última atualização: {data}

## Stack

| Camada | Tecnologia |
...

## Visão Geral
{diagrama 1}
{descrição}

## Fluxo de Extração
{diagrama 2}
{descrição}

## Cold Start — Novo Domínio
{diagrama 3}
{descrição}

## Ciclo de Vida do Schema
{diagrama 4}
{descrição}

## Modelo de Dados
{diagrama 5}
{descrição}

## Decisões Arquiteturais
Links para docs/adr/ com uma linha de contexto cada.
```

---

## Passo 5 — Verificar consistência

Antes de salvar, confirme:

- [ ] Todos os componentes no diagrama existem em `docs/specs/components.md`
- [ ] Todos os endpoints no diagrama existem em `docs/specs/api.md`
- [ ] Todos os termos usados existem no `CONTEXT.md` (sem sinônimos)
- [ ] A data de atualização está correta
- [ ] Se o código existir: nenhum componente no diagrama foi removido do código sem atualização aqui

Se houver divergência entre diagrama e código, adicione ao final do arquivo:

```markdown
## Divergências Conhecidas

- [ ] {componente}: spec diz X, código faz Y — revisar
```
