---
name: build-extraction-prompt
description: Use this skill to build or tune the LLM extraction prompt for a specific Domain. Use when extraction quality is low for a domain, when a new schema version is added, or when few-shot examples need to be refreshed. Produces a prompt ready to be used in the Extractor's Phase 2 (LLM).
---

# Build Extraction Prompt

Constrói ou ajusta o prompt de extração LLM para um Domínio específico, incorporando Schema, contexto do Domain Registration e Few-Shot Examples.

---

## Passo 1 — Carregar os dados do Domínio

```python
import httpx

# Buscar detalhes do domínio (schema atual + registration context)
resp = httpx.get(
    f"http://localhost:8000/api/v1/domains/{domain_id}",
    headers={"Authorization": f"Bearer {token}"}
)
domain = resp.json()

schema_fields = [f for f in domain["schema_fields"] if f["status"] == "active"]
```

---

## Passo 2 — Recuperar Few-Shot Examples do Qdrant

```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("neuralmind/bert-base-portuguese-cased")
client = QdrantClient(host="localhost", port=6333)

# Gerar embedding do PDF atual
embedding = model.encode(texto_do_pdf).tolist()

# Buscar exemplos similares filtrados pelo domínio
resultados = client.search(
    collection_name="few_shot_examples",
    query_vector=embedding,
    query_filter={"must": [{"key": "domain_id", "match": {"value": domain_id}}]},
    score_threshold=0.6,
    limit=5
)

few_shot_examples = [r.payload["extraction"] for r in resultados]
```

---

## Passo 3 — Construir o prompt

O prompt tem quatro seções obrigatórias nesta ordem:

### 3.1 — Instrução principal
```
Você é um extrator de dados de relatórios governamentais brasileiros.
Extraia apenas os campos listados abaixo do texto fornecido.
Retorne um JSON com exatamente os campos do schema.
Se um campo não for encontrado no texto, retorne null para esse campo.
Nunca invente valores. Nunca interpole ou estime.
```

### 3.2 — Schema do Domínio
```python
schema_str = "Schema esperado (domínio: {name}, órgão: {organ}):\n".format(**domain)
for field in schema_fields:
    schema_str += f"  - {field['name']} ({field['field_type']}): {field['description']}\n"
```

### 3.3 — Contexto do Domain Registration
```python
context_str = f"""
Contexto do relatório:
  Órgão: {domain['organ']}
  Descrição: {domain['context']}
  Periodicidade: {domain['periodicity']}
  Seções prioritárias: {', '.join(domain['priority_sections'])}
"""
```

### 3.4 — Few-Shot Examples
```python
examples_str = ""
for i, ex in enumerate(few_shot_examples, 1):
    examples_str += f"\nExemplo {i} de extração correta:\n"
    for campo, valor in ex.items():
        examples_str += f"  {campo}: {valor}\n"
```

### 3.5 — Montar prompt final
```python
prompt = f"""
{instrucao_principal}

{schema_str}

{context_str}

{examples_str}

Texto do relatório (campos já extraídos por parser determinístico foram removidos):
{texto_restante}

Retorne apenas o JSON com os campos extraídos. Sem explicações.
"""
```

---

## Passo 4 — Validar qualidade do prompt

Antes de salvar ou usar, verifique:

1. **Campos no schema** — todos os campos `active` estão listados?
2. **Few-shot suficientes** — há pelo menos 1 exemplo? Se não, avise que a primeira extração será sem exemplos (cold start).
3. **Campos já extraídos removidos** — o `texto_restante` não contém campos que o parser determinístico já extraiu (evita duplicação).
4. **Tamanho do prompt** — estime tokens (regra: ~4 chars/token). Se ultrapassar 180k tokens, reduza o número de few-shot examples.

---

## Passo 5 — Ajuste fino (quando a qualidade está baixa)

Se as extrações de um domínio estão com muitas Corrections, analise o padrão:

**Tipo de erro → ajuste no prompt:**

| Padrão de Correction | Ajuste |
|---|---|
| Campo sempre null quando existe | Adicionar dica de localização: "geralmente na seção X" |
| Valor com formato errado (data, moeda) | Especificar formato esperado: "retorne como YYYY-MM-DD" |
| Campo confundido com outro | Diferenciar na descrição: "não confundir com campo_y" |
| Valores de tabela perdidos | Adicionar instrução: "extraia todas as linhas da tabela, não apenas o total" |

Aplique o ajuste na descrição do campo em `schema_fields` ou na instrução principal, e documente a mudança para o admin.

---

## Saída esperada

Um prompt string pronto para ser enviado à Claude API:

```python
import anthropic

client = anthropic.Anthropic()
resposta = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
resultado = json.loads(resposta.content[0].text)
```
