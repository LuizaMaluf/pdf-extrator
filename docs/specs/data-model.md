# Data Model Spec

## PostgreSQL

### users
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | |
| username | varchar unique | |
| password_hash | varchar | bcrypt |
| role | enum('analyst','admin') | |
| created_at | timestamptz | |

---

### domains
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | |
| name | varchar unique | nome do tipo de relatório |
| organ | varchar | órgão de origem |
| context | text | contexto mínimo do Domain Registration |
| priority_sections | text[] | seções prioritárias |
| known_fields | jsonb | `[{name, description}]` — contexto original do Domain Registration, congelado; usado no prompt de cold start |
| periodicity | enum('annual','quarterly','monthly') | |
| created_by | uuid FK → users.id | |
| created_at | timestamptz | |

`known_fields` é preservado no formato simples `{name, description}` exatamente como registrado pelo admin. Ao criar o Domínio, cada item também vira um `schema_field` v1 com `field_type: string` e `status: active` — permitindo que o schema evolua independentemente sem alterar o contexto original.

---

### schema_versions
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | |
| domain_id | uuid FK → domains.id | |
| version | integer | incremento por domínio |
| status | enum('draft','validated') | |
| created_at | timestamptz | |

Constraint: `(domain_id, version)` unique.  
A versão ativa de um domínio é a de maior `version`.

---

### schema_fields
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | |
| domain_id | uuid FK → domains.id | |
| name | varchar | |
| description | text | |
| field_type | enum('string','number','date','table') | |
| status | enum('active','deprecated') | |
| added_in_version | integer FK → schema_versions.version | |
| deprecated_in_version | integer FK → schema_versions.version \| null | |

---

### extraction_jobs
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | job_id exposto na API |
| pdf_path | varchar | caminho no filesystem local |
| domain_id | uuid FK → domains.id \| null | null até classificação |
| schema_version_id | uuid FK → schema_versions.id \| null | definido no início da extração |
| status | enum('pending','processing','needs_confirmation','needs_registration','completed','validated','failed') | |
| confidence | float \| null | score da classificação automática |
| period_reference | daterange \| null | período de referência do documento (ex: `[2024-01-01,2024-03-31]`); extraído pelo LLM; permite filtro overlap via `&&` |
| result | jsonb \| null | campos extraídos (fase 1 + fase 2) |
| error | text \| null | mensagem de erro se `failed` |
| created_by | uuid FK → users.id | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

Query de filtro por período: `period_reference && daterange(period_start, period_end)`. O LLM é instruído a retornar o período de referência como intervalo de datas (primeiro e último dia do período coberto pelo documento). A API formata o `daterange` como string legível na resposta.

---

### corrections
| coluna | tipo | notas |
|---|---|---|
| id | uuid PK | |
| job_id | uuid FK → extraction_jobs.id | |
| field_name | varchar | |
| original_value | jsonb | valor extraído antes da correção |
| corrected_value | jsonb | valor após correção do validador |
| is_new_field | boolean | true se campo não existia no schema |
| created_by | uuid FK → users.id | |
| created_at | timestamptz | |

---

## Qdrant

### Coleção: `domain_signatures`
Usada pelo Domain Classifier para identificar o Domínio de novos PDFs.

| campo | tipo | notas |
|---|---|---|
| id | uuid | domain_id |
| vector | float[] | embedding do contexto do Domain Registration |
| payload.domain_id | uuid | |
| payload.name | string | |
| payload.organ | string | |

---

### Coleção: `few_shot_examples`
Usada pelo Few-Shot Retriever para recuperar exemplos por similaridade.

| campo | tipo | notas |
|---|---|---|
| id | uuid | job_id da extração validada |
| vector | float[] | embedding do texto do PDF |
| payload.domain_id | uuid | usado no filtro da busca |
| payload.schema_version | integer | versão do schema no momento da validação |
| payload.extraction | object | campos extraídos após todas as Corrections |

Busca sempre filtrada por `payload.domain_id == X`.  
Score mínimo para inclusão no prompt: 0.6.  
Máximo de exemplos retornados: 5.
