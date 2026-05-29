# API Spec

Base URL: `/api/v1`  
Autenticação: Bearer JWT em todos os endpoints exceto `/auth/token`  
Roles: `analyst` (upload + validation), `admin` (+ gestão de domínios e schemas)

---

## Auth

### POST /auth/token
Gera JWT para um usuário.

**Request**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "role": "analyst | admin"
}
```

---

## Upload & Jobs

### POST /pdfs
Upload de um PDF. Dispara um Extraction Job assíncrono.

**Request**: `multipart/form-data`
- `file` (PDF, obrigatório)
- `domain_id` (string, opcional) — se omitido, o sistema tenta classificar automaticamente

**Response 202**
```json
{
  "job_id": "uuid",
  "status": "pending"
}
```

---

### GET /jobs/{job_id}
Retorna status e resultado de um Extraction Job.

**Response 200**
```json
{
  "job_id": "uuid",
  "status": "pending | processing | needs_confirmation | needs_registration | completed | validated | failed",
  "domain_id": "uuid | null",
  "confidence": 0.87,
  "schema_version_id": "uuid | null",
  "result": { },
  "error": "string | null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

`result` está presente quando `status` é `completed` ou `validated`.  
`confidence` está presente quando o sistema classificou o domínio automaticamente.

---

### POST /jobs/{job_id}/confirm-domain
Confirma ou corrige o Domínio de um job com `status: needs_confirmation`.  
Role: `analyst+`

**Request**
```json
{
  "domain_id": "uuid"
}
```

**Response 200**
```json
{
  "job_id": "uuid",
  "status": "processing"
}
```

---

## Domínios

### GET /domains
Lista todos os Domínios registrados.  
Role: `analyst+`

**Response 200**
```json
[
  {
    "id": "uuid",
    "name": "string",
    "organ": "string",
    "periodicity": "annual | quarterly | monthly",
    "schema_status": "draft | validated",
    "schema_version": "integer",
    "created_at": "ISO8601"
  }
]
```

---

### POST /domains
Registra um novo Domínio (Domain Registration).  
Role: `admin`

**Request**
```json
{
  "name": "string",
  "organ": "string",
  "context": "string",
  "priority_sections": ["string"],
  "known_fields": [
    { "name": "string", "description": "string" }
  ],
  "periodicity": "annual | quarterly | monthly"
}
```

**Response 201**
```json
{
  "id": "uuid",
  "name": "string",
  "schema_status": "draft",
  "schema_version": 1
}
```

---

### GET /domains/{domain_id}
Retorna detalhes do Domínio incluindo o Schema atual.  
Role: `analyst+`

**Response 200**
```json
{
  "id": "uuid",
  "name": "string",
  "organ": "string",
  "context": "string",
  "priority_sections": ["string"],
  "known_fields": [{ "name": "string", "description": "string" }],
  "periodicity": "annual | quarterly | monthly",
  "schema_status": "draft | validated",
  "schema_version": "integer",
  "schema_fields": [
    {
      "name": "string",
      "type": "string | number | date | table",
      "status": "active | deprecated",
      "added_in_version": "integer"
    }
  ],
  "created_at": "ISO8601"
}
```

---

### POST /domains/{domain_id}/schema/validate
Declara o Schema atual do Domínio como `validated`.  
Role: `admin`

**Response 200**
```json
{
  "domain_id": "uuid",
  "schema_status": "validated",
  "schema_version": "integer"
}
```

---

## Validação

### GET /jobs/{job_id}/validation
Retorna os dados extraídos para revisão humana.  
Role: `analyst+`

**Response 200**
```json
{
  "job_id": "uuid",
  "domain_id": "uuid",
  "schema_version_id": "uuid",
  "pdf_url": "string",
  "fields": [
    {
      "name": "string",
      "extracted_value": "any",
      "corrected_value": "any | null",
      "source": "deterministic | llm",
      "status": "pending | corrected | confirmed"
    }
  ]
}
```

`pdf_url` aponta para o arquivo original servido pela própria API para exibição no HTMX.

---

### PATCH /jobs/{job_id}/validation
Submete Corrections campo a campo.  
Role: `analyst+`

**Request**
```json
{
  "corrections": [
    {
      "field_name": "string",
      "corrected_value": "any"
    }
  ],
  "new_fields": [
    {
      "name": "string",
      "value": "any",
      "type": "string | number | date | table"
    }
  ]
}
```

`new_fields` permite ao validador adicionar campos que o sistema não extraiu, evoluindo o Schema.

**Response 200**
```json
{
  "job_id": "uuid",
  "status": "validated",
  "schema_evolved": true,
  "new_schema_version": "integer | null"
}
```

---

## Query

### GET /domains/{domain_id}/extractions
Consulta extrações validadas de um Domínio.  
Role: `analyst+`

**Query params**
- `period_start` (date, opcional) — filtro de período de referência início
- `period_end` (date, opcional) — filtro de período de referência fim
- `schema_version` (integer, opcional) — filtra por versão de schema
- `page` (integer, default 1)
- `page_size` (integer, default 20, max 100)

**Response 200**
```json
{
  "total": 142,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "job_id": "uuid",
      "schema_version": "integer",
      "period_reference": "string",
      "validated_at": "ISO8601",
      "data": { }
    }
  ]
}
```

`data` contém os campos extraídos e validados conforme o Schema da versão vinculada.
