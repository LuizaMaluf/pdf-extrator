---
name: register-domain
description: Use this skill when a PDF of an unknown Domain arrives and needs to be registered via Domain Registration. Analyzes the PDF content and proposes values for all required registration fields (organ, context, priority_sections, known_fields, periodicity), then calls POST /domains after admin confirmation.
---

# Domain Registration

Registra um novo Domínio analisando o PDF e propondo os campos do Domain Registration para confirmação do admin.

---

## Passo 1 — Ler o PDF

```python
import pdfplumber

with pdfplumber.open(caminho_do_pdf) as pdf:
    # Primeiras 3 páginas são suficientes para identificar estrutura
    texto = "\n".join(p.extract_text() or "" for p in pdf.pages[:3])
    tabelas = []
    for p in pdf.pages[:3]:
        tabelas.extend(p.extract_tables() or [])
```

---

## Passo 2 — Inferir os campos do Domain Registration

Com base no texto e tabelas extraídos, analise e proponha:

**`organ`** — Procure no cabeçalho, rodapé ou primeira página por:
- Nome de ministério, secretaria, autarquia ou agência governamental
- Siglas comuns: MS, MEC, MF, MAPA, FUNASA, IBGE, etc.

**`context`** — Resuma em 2–3 frases o que o relatório reporta:
- Qual período de referência cobre
- Que tipo de dado contém (financeiro, epidemiológico, orçamentário, etc.)
- Para que audiência parece ser destinado

**`priority_sections`** — Liste as seções/capítulos mais relevantes encontrados no sumário ou nos cabeçalhos de página. Máximo 5 seções.

**`known_fields`** — Identifique campos concretos que claramente existem no documento. Mínimo 2, máximo 8. Exemplos:
```
- name: "total_despesas_empenhadas", description: "valor total empenhado no período"
- name: "percentual_executado", description: "percentual do orçamento executado"
- name: "data_referencia", description: "mês/ano de referência do relatório"
```

**`periodicity`** — Infira a partir de:
- Título do documento ("Relatório Anual", "Boletim Trimestral", "Informe Mensal")
- Datas presentes no texto
- Padrão de numeração de edições

---

## Passo 3 — Apresentar proposta ao admin

Mostre a proposta completa antes de qualquer chamada à API:

```
Domínio identificado: [nome proposto]

organ:             Ministério da Saúde
context:           Relatório mensal de execução orçamentária do Fundo Nacional de Saúde,
                   cobrindo empenho, liquidação e pagamento por programa de trabalho.
priority_sections: ["Execução por Programa", "Demonstrativo de Restos a Pagar",
                    "Comparativo com Exercício Anterior"]
known_fields:
  - total_despesas_empenhadas: valor total empenhado no período
  - total_liquidado: valor total liquidado
  - total_pago: valor total pago
  - percentual_executado: percentual do orçamento executado
  - mes_referencia: mês de referência
periodicity:       monthly

Confirma ou corrige?
```

Aguarde confirmação ou correções antes de prosseguir.

---

## Passo 4 — Chamar POST /domains

Após confirmação:

```python
import httpx

payload = {
    "name": nome_do_dominio,
    "organ": organ,
    "context": context,
    "priority_sections": priority_sections,
    "known_fields": [{"name": f["name"], "description": f["description"]} for f in known_fields],
    "periodicity": periodicity
}

resp = httpx.post(
    "http://localhost:8000/api/v1/domains",
    json=payload,
    headers={"Authorization": f"Bearer {token_admin}"}
)
resp.raise_for_status()
domain = resp.json()
print(f"Domínio criado: {domain['id']} | Schema: draft v{domain['schema_version']}")
```

---

## Passo 5 — Reprocessar o job pendente

Após criação do Domínio, o job original está em `needs_registration`. Confirme o domínio:

```python
resp = httpx.post(
    f"http://localhost:8000/api/v1/jobs/{job_id}/confirm-domain",
    json={"domain_id": domain["id"]},
    headers={"Authorization": f"Bearer {token_admin}"}
)
resp.raise_for_status()
print("Job reenfileirado para extração.")
```

---

## Casos especiais

**PDF sem texto selecionável (escaneado)**: use OCR antes do passo 1:
```bash
pip install pytesseract pdf2image
sudo apt-get install tesseract-ocr tesseract-ocr-por
```
```python
from pdf2image import convert_from_path
import pytesseract
imagens = convert_from_path(caminho_do_pdf)
texto = "\n".join(pytesseract.image_to_string(img, lang='por') for img in imagens[:3])
```

**Domínio ambíguo** (parece similar a um já existente): liste os domínios existentes via `GET /domains` e compare. Se for o mesmo tipo de relatório de outro órgão, pode ser um novo Domínio ou uma variante — pergunte ao admin antes de criar.
