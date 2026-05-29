---
name: evolve-schema
description: Use this skill to analyze accumulated Corrections for a Domain and suggest schema evolution — new fields to add, fields to deprecate, and whether the schema is ready to be declared validated. Use after a domain has received 5+ validations, or when the admin wants to review schema quality.
---

# Evolve Schema

Analisa as Corrections acumuladas de um Domínio e propõe evoluções de Schema: campos novos a adicionar, campos a deprecar, e se o Schema está maduro o suficiente para ser declarado `validated`.

---

## Passo 1 — Carregar Corrections do Domínio

```python
import httpx
import psycopg2

conn = psycopg2.connect(dsn)
cur = conn.cursor()

# Buscar todas as corrections do domínio (via jobs vinculados)
cur.execute("""
    SELECT c.field_name, c.original_value, c.corrected_value, c.is_new_field, c.created_at
    FROM corrections c
    JOIN extraction_jobs j ON j.id = c.job_id
    WHERE j.domain_id = %s
    ORDER BY c.created_at DESC
""", (domain_id,))

corrections = cur.fetchall()
print(f"Total de corrections: {len(corrections)}")
```

---

## Passo 2 — Analisar padrões

Agrupe as Corrections por campo e calcule métricas:

```python
from collections import defaultdict

por_campo = defaultdict(list)
for field_name, original, corrected, is_new, created_at in corrections:
    por_campo[field_name].append({
        "original": original,
        "corrected": corrected,
        "is_new": is_new
    })

analise = {}
for campo, corrs in por_campo.items():
    total = len(corrs)
    novos = sum(1 for c in corrs if c["is_new"])
    analise[campo] = {
        "total_corrections": total,
        "is_new_field": novos == total,  # campo surgiu só via new_fields
        "correction_rate": total,        # quantas vezes foi corrigido
    }
```

---

## Passo 3 — Gerar proposta de evolução

Com base na análise, classifique cada campo em uma das categorias:

### Campos novos a adicionar ao Schema
Critério: apareceu em `new_fields` em **3 ou mais** Corrections diferentes.
```python
candidatos_adicionar = [
    campo for campo, dados in analise.items()
    if dados["is_new_field"] and dados["total_corrections"] >= 3
]
```

### Campos do Schema atual a deprecar
Critério: nunca apareceu em nenhuma extração validada (ausente em todos os resultados de jobs `validated`).
```python
cur.execute("""
    SELECT DISTINCT sf.name
    FROM schema_fields sf
    WHERE sf.domain_id = %s AND sf.status = 'active'
    AND sf.name NOT IN (
        SELECT DISTINCT c.field_name
        FROM corrections c
        JOIN extraction_jobs j ON j.id = c.job_id
        WHERE j.domain_id = %s AND j.status = 'validated'
    )
    AND sf.name NOT IN (
        SELECT jsonb_object_keys(j.result)
        FROM extraction_jobs j
        WHERE j.domain_id = %s AND j.status = 'validated'
    )
""", (domain_id, domain_id, domain_id))
candidatos_deprecar = [r[0] for r in cur.fetchall()]
```

### Avaliação de maturidade para `validated`
O Schema está pronto para ser declarado `validated` quando:
- Há **10 ou mais** jobs com status `validated` para o domínio
- A taxa de corrections por job está abaixo de **2 corrections/job** (em média)
- Nenhum campo novo apareceu nas últimas **5 validações**

```python
cur.execute("SELECT COUNT(*) FROM extraction_jobs WHERE domain_id = %s AND status = 'validated'", (domain_id,))
total_validados = cur.fetchone()[0]

media_corrections = len(corrections) / max(total_validados, 1)
pronto_para_validated = (
    total_validados >= 10 and
    media_corrections < 2 and
    not candidatos_adicionar  # nenhum campo novo recente
)
```

---

## Passo 4 — Apresentar proposta ao admin

```
Análise do Schema — Domínio: [nome]
Jobs validados: 14 | Total de corrections: 23 | Média: 1.6/job

CAMPOS PARA ADICIONAR (apareceram em ≥3 validações):
  + valor_residual       → "valor residual não executado do período"  (8 ocorrências)
  + fonte_recurso        → "fonte de recurso orçamentário"            (4 ocorrências)

CAMPOS PARA DEPRECAR (nunca extraídos em jobs validados):
  - codigo_acao          → nunca apareceu em nenhuma extração validada

MATURIDADE:
  ✓ Schema pronto para ser declarado validated
  (14 jobs validados, média 1.6 corrections/job, nenhum campo novo nas últimas 5 validações)

Aplicar essas mudanças? (s/n)
```

Aguarde confirmação antes de qualquer chamada à API.

---

## Passo 5 — Aplicar as mudanças

### Adicionar campos novos
```python
# Feito via PATCH /jobs/{job_id}/validation com new_fields
# OU diretamente via endpoint de admin (se disponível)
# Por ora, oriente o admin a incluir os campos na próxima Validation
print("Instrução: inclua os campos abaixo como new_fields na próxima Validation:")
for campo in candidatos_adicionar:
    print(f"  - {campo}")
```

### Deprecar campos
```python
cur.execute("""
    UPDATE schema_fields
    SET status = 'deprecated', deprecated_in_version = (
        SELECT MAX(version) FROM schema_versions WHERE domain_id = %s
    )
    WHERE domain_id = %s AND name = ANY(%s)
""", (domain_id, domain_id, candidatos_deprecar))
conn.commit()
print(f"Campos deprecados: {candidatos_deprecar}")
```

### Declarar Schema como validated
```python
resp = httpx.post(
    f"http://localhost:8000/api/v1/domains/{domain_id}/schema/validate",
    headers={"Authorization": f"Bearer {token_admin}"}
)
resp.raise_for_status()
print(f"Schema declarado validated: v{resp.json()['schema_version']}")
```

---

## Quando não evoluir

Não proponha evolução se:
- Menos de 5 jobs validados — amostra insuficiente para padrões confiáveis
- O domínio recebeu PDFs de períodos muito diferentes — a variação pode ser sazonal, não estrutural
- Um campo novo apareceu apenas 1–2 vezes — pode ser anomalia de um relatório específico

Nesses casos, informe o admin e aguarde mais validações.
