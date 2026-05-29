# PDF Extractor

Pipeline para extração estruturada de dados de relatórios governamentais em PDF com layouts e conteúdos heterogêneos. Organizado por tipo de relatório (**Domínio**), com aprendizado contínuo via feedback humano e API para consulta estruturada dos dados extraídos por Domínio e período.

---

## O que faz

Recebe PDFs de relatórios governamentais de diferentes ministérios e órgãos, identifica o tipo de relatório, extrai os dados de forma estruturada e expõe esses dados via API. A qualidade da extração melhora continuamente conforme validadores humanos corrigem os resultados.

---

## Como funciona

1. **Upload** — um PDF é enviado via API; um job assíncrono é criado
2. **Classificação** — o sistema identifica o Domínio (tipo de relatório) automaticamente; se a confiança for baixa, um humano confirma
3. **Extração híbrida** — parser determinístico (pdfplumber + camelot) cobre campos estruturados; Claude API cobre o restante usando exemplos de extrações anteriores similares
4. **Validação** — um validador humano revisa e corrige campo a campo via interface web
5. **Aprendizado** — cada correção vira um exemplo para extrações futuras do mesmo tipo de relatório; o schema do domínio evolui com novos campos descobertos
6. **Consulta** — dados extraídos e validados ficam disponíveis via API com filtros por período

---

## Stack

| Camada | Tecnologia |
|---|---|
| API + Frontend | FastAPI + HTMX + Jinja2 |
| Job Queue | Celery + Redis |
| Banco de dados | PostgreSQL + SQLAlchemy + Alembic |
| Vector store | Qdrant |
| Embeddings | sentence-transformers (`neuralmind/bert-base-portuguese-cased`) |
| PDF (determinístico) | pdfplumber + camelot |
| LLM | Claude API (Anthropic SDK) |
| Infraestrutura | Docker Compose |

Todas as ferramentas são open source, exceto a Claude API.

---

## Conceitos centrais

| Termo | Definição |
|---|---|
| **Domínio** | Tipo específico de relatório com estrutura própria. Um ministério pode ter múltiplos Domínios. |
| **Extractor** | Lógica de extração de um Domínio (determinístico + LLM). Um por Domínio. |
| **Schema** | Conjunto de campos esperados de um Domínio. Evolui de `draft` para `validated`. |
| **Extraction Job** | Unidade assíncrona de trabalho disparada por um upload. Retorna `job_id`. |
| **Validation** | Revisão humana com correção campo a campo do resultado extraído. |
| **Correction** | Edição de campo feita durante Validation. Alimenta os exemplos de extração futura. |
| **Few-Shot Example** | Extração corrigida usada como exemplo no prompt do LLM. Selecionada por similaridade semântica. |
| **Domain Registration** | Protocolo de onboarding para PDFs de Domínio desconhecido. |

Glossário completo em [CONTEXT.md](CONTEXT.md).

---

## Documentação

| Arquivo | Conteúdo |
|---|---|
| [CONTEXT.md](CONTEXT.md) | Glossário do domínio — termos canônicos e relações |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diagramas de arquitetura e fluxos (Mermaid) |
| [docs/specs/api.md](docs/specs/api.md) | Contratos dos endpoints (request/response/roles) |
| [docs/specs/components.md](docs/specs/components.md) | Especificação de cada componente interno |
| [docs/specs/data-model.md](docs/specs/data-model.md) | Tabelas PostgreSQL e coleções Qdrant |
| [docs/adr/](docs/adr/) | Decisões arquiteturais registradas |

---

## Skills disponíveis

| Skill | Quando usar |
|---|---|
| `/register-domain` | PDF de tipo desconhecido chegou — registra um novo Domínio |
| `/build-extraction-prompt` | Qualidade de extração de um Domínio caiu — ajusta o prompt do LLM |
| `/evolve-schema` | Domínio tem ≥5 validações — analisa Corrections e sugere evolução de Schema |
| `/update-docs` | Qualquer mudança de componente, endpoint ou tabela — atualiza ARCHITECTURE.md |

---

## Perfis de acesso

| Role | Pode fazer |
|---|---|
| `analyst` | Upload de PDFs, Validation (correções campo a campo), consulta de dados |
| `admin` | Tudo do analyst + criar Domínios, declarar Schema como `validated` |
