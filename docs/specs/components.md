# Component Specs

## 1. Domain Classifier

Responsável por identificar o Domínio de um PDF recém-carregado.

**Entrada**: arquivo PDF + metadados do upload (nome, domain_id opcional)  
**Saída**: `domain_id`, `confidence` (0.0–1.0)

**Fluxo**:
1. Se `domain_id` foi fornecido no upload → `confidence: 1.0`, pula classificação
2. Extrai texto da primeira página e cabeçalho via pdfplumber
3. Gera embedding do texto extraído via sentence-transformers
4. Busca no Qdrant (coleção `domain_signatures`) o Domínio mais similar
5. Se `confidence >= 0.85` → prossegue automaticamente
6. Se `confidence < 0.85` → job muda para `needs_confirmation`, aguarda humano

**Threshold de confiança**: 0.85 (configurável via variável de ambiente)

---

## 2. Extractor

Pipeline híbrido de extração em duas fases para um Domínio conhecido.

**Entrada**: PDF, Domain (com Schema e Domain Registration), Few-Shot Examples  
**Saída**: dicionário de campos extraídos com `source: deterministic | llm`

### Fase 1 — Determinística
Executada por pdfplumber + camelot. Responsável por:
- Tabelas com bordas (camelot lattice)
- Tabelas sem bordas (camelot stream)
- Campos com padrão fixo: datas, códigos, valores monetários (regex)
- Metadados do PDF (título, autor, data de criação)

Campos extraídos nessa fase são marcados `source: deterministic` e não passam pelo LLM.

### Fase 2 — LLM (Claude API)
Processa o conteúdo restante não coberto pela fase determinística.

**Prompt construído com**:
- Schema do Domínio (campos esperados com tipos e descrições)
- Contexto do Domain Registration (órgão, contexto, seções prioritárias)
- Campos já extraídos na fase 1 (para evitar duplicação)
- N Few-Shot Examples recuperados por similaridade semântica (ver componente 3)

**Instrução ao LLM**: extrair apenas campos do Schema ainda ausentes. Se um campo não for encontrado, retornar `null` — nunca inventar valores.

**Schema Version**: a versão ativa no momento da execução é registrada no job e imutável após a extração.

---

## 3. Few-Shot Retriever

Recupera os Few-Shot Examples mais relevantes para guiar o LLM na extração.

**Entrada**: texto do PDF atual, `domain_id`  
**Saída**: lista ordenada de até N exemplos (extração + correções)

**Fluxo**:
1. Gera embedding do texto do PDF atual via sentence-transformers
2. Busca no Qdrant (coleção `few_shot_examples`) com filtro `domain_id == X`
3. Retorna os top-N por score de similaridade coseno
4. N máximo: 5 (configurável). Exemplos com score < 0.6 são descartados.

**Formato de cada exemplo no prompt**:
```
PDF (trecho): "..."
Extração correta:
  campo_a: valor_a
  campo_b: valor_b
```

---

## 4. Schema Registry

Gerencia o ciclo de vida dos Schemas por Domínio.

**Estados**: `draft` → `validated`  
**Responsável pela transição**: `admin` via `POST /domains/{id}/schema/validate`

**Ao criar um Domínio** (Domain Registration):
- Schema Version 1 criada com status `draft`
- Campos iniciais: os `known_fields` fornecidos no registro

**Ao submeter Corrections com `new_fields`**:
1. Campos novos adicionados ao Schema do Domínio
2. Nova Schema Version criada (incremento inteiro)
3. Schema Version anterior mantida imutável (histórico)
4. Jobs anteriores continuam vinculados à versão em que foram executados

**Campos `deprecated`**:
- Nunca removidos do Schema
- Marcados como `deprecated` na Schema Version atual
- Não incluídos no prompt do LLM para novos jobs
- Retornados na query apenas quando filtrado pela versão que os continha

---

## 5. Correction Processor

Processa Corrections submetidas na Validation e alimenta o sistema de aprendizado.

**Fluxo ao receber PATCH /jobs/{job_id}/validation**:
1. Persiste cada Correction no Postgres (campo, valor original, valor corrigido, job_id)
2. Monta o Few-Shot Example completo: texto do PDF + todos os campos após correção
3. Gera embedding do texto do PDF via sentence-transformers
4. Upsert no Qdrant (coleção `few_shot_examples`) com metadata `domain_id`
5. Se `new_fields` presentes → aciona Schema Registry para criar nova Schema Version
6. Atualiza status do job para `validated`

---

## 6. Domain Registration Handler

Ativado quando um job entra em `needs_registration`.

**Fluxo**:
1. Admin acessa `POST /domains` com as informações coletadas
2. Domain Registration cria o Domínio e Schema Version 1 (`draft`)
3. Gera embedding do contexto do Domínio e indexa no Qdrant (`domain_signatures`)
4. Job pendente é reenfileirado no Celery com o novo `domain_id`
5. Extractor roda com Schema Version 1 e sem Few-Shot Examples (cold start)
