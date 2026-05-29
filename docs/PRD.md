# PRD — PDF Extractor

## Problem Statement

Analistas de ciência política e tecnologia precisam extrair dados estruturados de centenas de relatórios governamentais em PDF produzidos por diferentes ministérios e órgãos. Cada relatório tem layout, vocabulário e estrutura próprios. Hoje esse trabalho é manual: o analista lê o PDF, identifica os campos relevantes e os transcreve para uma planilha. O processo é lento, propenso a erro e não escala — novos relatórios chegam continuamente, e cada tipo novo exige reaprendizado do que extrair e de onde.

## Solution

Um pipeline assíncrono que recebe PDFs via API, identifica automaticamente o tipo de relatório (Domínio), extrai os dados usando uma combinação de parser determinístico e LLM, e expõe o resultado para revisão humana campo a campo. Cada correção do validador alimenta extrações futuras do mesmo Domínio, melhorando progressivamente a qualidade sem reprocessamento manual. Os dados extraídos e validados ficam disponíveis via API com filtros por Domínio e período, prontos para análise.

## User Stories

1. Como analista, quero fazer upload de um PDF via API, para que o sistema processe a extração sem eu precisar acompanhar em tempo real.
2. Como analista, quero receber um `job_id` ao fazer upload, para que eu possa consultar o status da extração quando quiser.
3. Como analista, quero que o sistema identifique automaticamente o tipo de relatório (Domínio), para que eu não precise classificar cada PDF manualmente.
4. Como analista, quero ser notificado quando a confiança da classificação for baixa, para que eu possa confirmar o Domínio antes da extração prosseguir.
5. Como analista, quero ver o resultado da extração com os campos organizados lado a lado com o PDF, para que eu possa revisar sem alternar entre ferramentas.
6. Como analista, quero corrigir campos errados ou ausentes campo a campo, para que eu não precise rejeitar e reprocessar o documento inteiro.
7. Como analista, quero que minhas correções alimentem automaticamente extrações futuras do mesmo tipo de relatório, para que o sistema aprenda sem eu precisar configurar nada.
8. Como analista, quero consultar todos os dados extraídos e validados de um Domínio, filtrados por período de referência, para que eu possa usar os dados diretamente em análises.
9. Como analista de ciência política, quero usar a interface de validação sem conhecimento técnico, para que eu possa contribuir com qualidade sem depender do time de tecnologia.
10. Como analista, quero poder adicionar campos que o sistema não extraiu durante a validação, para que dados importantes não se percam mesmo quando o sistema não os reconheceu.
11. Como admin, quero registrar um novo tipo de relatório informando órgão, contexto, seções prioritárias, campos conhecidos e periodicidade, para que o sistema saiba o que extrair na primeira tentativa.
12. Como admin, quero que o sistema faça uma primeira tentativa de extração logo após o Domain Registration, para que o ciclo de validação comece imediatamente.
13. Como admin, quero declarar o Schema de um Domínio como `validated` quando estiver maduro, para que ele passe a ser o contrato oficial de extrações futuras.
14. Como admin, quero que campos obsoletos sejam marcados como `deprecated` sem serem removidos, para que extrações antigas continuem sendo consultáveis no formato em que foram geradas.
15. Como admin, quero analisar as correções acumuladas de um Domínio e receber sugestões de evolução do Schema, para que o Schema reflita o que o sistema realmente extrai.
16. Como admin, quero que cada Extraction Job fique vinculado à Schema Version ativa no momento da extração, para que mudanças futuras de schema não alterem registros já validados.
17. Como admin, quero que o reprocessamento de um PDF com uma Schema Version mais nova seja sempre explícito e manual, para que dados validados não sejam sobrescritos sem intenção.
18. Como admin, quero gerenciar os perfis de acesso (analyst / admin), para que validadores de ciência política não possam alterar schemas ou criar domínios.
19. Como admin, quero que o Domain Classifier use similaridade semântica contra os domínios existentes para classificar novos PDFs, para que a classificação não dependa de regras manuais.
20. Como admin, quero que os Few-Shot Examples sejam selecionados por similaridade semântica com o PDF atual (não por recência), para que os exemplos mais estruturalmente parecidos guiem a extração.
21. Como admin, quero que o parser determinístico rode antes do LLM e cubra tabelas e campos com padrão fixo, para que o LLM só processe o que é genuinamente não estruturado.
22. Como admin, quero que o LLM retorne `null` para campos não encontrados, nunca inventando valores, para que dados ausentes sejam explícitos e não silenciosamente incorretos.
23. Como admin, quero acompanhar o status de cada Extraction Job (pending, processing, needs_confirmation, needs_registration, completed, validated, failed), para que eu possa identificar gargalos no pipeline.

## Implementation Decisions

### Módulos principais

#### 1. DomainClassifier
Recebe texto extraído do PDF e retorna `(domain_id, confidence)`. Encapsula a busca vetorial no Qdrant (`domain_signatures`) e a comparação com o threshold de confiança (0.85, configurável por variável de ambiente). Se `domain_id` é fornecido no upload, retorna `confidence: 1.0` sem busca. Interface simples e testável em isolamento com um Qdrant mockado.

#### 2. DeterministicExtractor
Recebe o caminho do PDF e o Schema do Domínio. Usa pdfplumber para texto e tabelas simples; camelot lattice para tabelas com bordas; camelot stream para tabelas sem bordas; regex para campos com padrão fixo (datas, valores monetários, códigos). Retorna dict de campos extraídos marcados com `source: deterministic`. Não acessa rede — testável com PDFs de fixture.

#### 3. FewShotRetriever
Recebe texto do PDF e `domain_id`. Gera embedding via sentence-transformers (`neuralmind/bert-base-portuguese-cased`), busca no Qdrant `few_shot_examples` com filtro `domain_id`, retorna top-5 com score ≥ 0.6. Testável com Qdrant mockado ou em memória.

#### 4. ExtractionPromptBuilder
Recebe Schema, contexto do Domain Registration, Few-Shot Examples e texto restante (após extração determinística). Monta o prompt em quatro seções ordenadas: instrução principal, schema, contexto, exemplos. Retorna string. Módulo puro — sem efeitos colaterais, testável com inputs simples.

#### 5. LLMExtractor
Recebe o prompt e chama a Claude API. Parseia o JSON da resposta. Retorna dict de campos com `source: llm`. Trata erros de rate limit com retry exponencial. Testável com Claude API mockada.

#### 6. ExtractionOrchestrator (Celery Worker)
Coordena o pipeline: DomainClassifier → DeterministicExtractor → FewShotRetriever → ExtractionPromptBuilder → LLMExtractor → persiste no PostgreSQL. Atualiza o status do job a cada etapa. Não contém lógica de negócio — delega tudo para os módulos acima.

#### 7. SchemaRegistry
Gerencia CRUD de Schema e seu ciclo de vida (`draft` → `validated`). Operações: `get_active(domain_id)`, `add_field(domain_id, field)`, `deprecate_field(domain_id, field_name)`, `validate(domain_id)`. Cada chamada que muda campos cria uma nova SchemaVersion imutável. Testável com PostgreSQL de teste.

#### 8. CorrectionProcessor
Recebe `job_id` e lista de Corrections. Persiste cada Correction no PostgreSQL. Monta o Few-Shot Example completo (texto do PDF + todos os campos pós-correção). Upserta no Qdrant. Se há `new_fields`, aciona SchemaRegistry. Atualiza status do job para `validated`. Testável com PostgreSQL e Qdrant de teste.

#### 9. DomainRegistrationHandler
Recebe os campos do Domain Registration (organ, context, priority_sections, known_fields, periodicity). Cria o Domain e Schema v1 (`draft`) no PostgreSQL. Gera embedding do contexto e indexa no Qdrant `domain_signatures`. Retorna o Domain criado.

#### 10. API Layer (FastAPI)
Roteamento HTTP, middleware de autenticação JWT (roles: analyst, admin), validação de request/response com Pydantic. Serve os templates HTMX para a interface de Validation. Endpoints conforme [docs/specs/api.md](specs/api.md).

#### 11. ValidationUI (HTMX + Jinja2)
Interface web mínima servida pelo próprio FastAPI. Exibe o PDF (via `<iframe>` ou `<embed>`) ao lado dos campos extraídos em formulário editável. Submete Corrections via `PATCH /jobs/:id/validation` com HTMX. Acessível a analistas de ciência política sem conhecimento técnico.

### Decisões arquiteturais

- **Extração assíncrona**: upload retorna `job_id`; processamento via Celery + Redis. Polling de status pelo cliente.
- **Hibridismo determinístico + LLM**: parser determinístico primeiro (campos estruturados), LLM para o restante. Campos determinísticos não são reenviados ao LLM.
- **Schema imutável por job**: cada Extraction Job registra a SchemaVersion ativa no momento. Reprocessamento com versão mais nova é sempre manual e explícito.
- **Few-Shot por similaridade semântica**: modelo `neuralmind/bert-base-portuguese-cased` — relatórios em PT-BR com jargão técnico governamental.
- **Qdrant para vector store**: filtragem nativa por `domain_id` na busca vetorial. pgvector descartado por performance insuficiente com filtros.
- **Celery + Redis**: suporte nativo a retries (falha de Claude API), prioridades e task chaining para reprocessamento explícito.
- **Autenticação JWT**: roles no payload. Analyst: upload + validation. Admin: + gestão de Domínios e Schemas.

### Contratos de API

Documentados em [docs/specs/api.md](specs/api.md). Estados do Extraction Job:

```
pending → processing → completed → validated
              ↓              ↑
     needs_confirmation ─────┘
     needs_registration → [Domain Registration] → processing
              ↓
           failed
```

### Data model

Documentado em [docs/specs/data-model.md](specs/data-model.md). Tabelas PostgreSQL: `users`, `domains`, `schema_versions`, `schema_fields`, `extraction_jobs`, `corrections`. Coleções Qdrant: `domain_signatures`, `few_shot_examples`.

## Testing Decisions

**O que faz um bom teste aqui**: testar o comportamento externo do módulo (o que entra, o que sai), não sua implementação interna. Um teste de DomainClassifier verifica que PDFs de domínios conhecidos retornam o `domain_id` correto com confidence alta — não verifica qual query foi feita ao Qdrant.

**Módulos a testar em isolamento (unit/integration):**

- **DeterministicExtractor** — testar com PDFs de fixture (um por Domínio conhecido). Verificar que campos esperados são extraídos com os valores corretos. Não requer rede.
- **ExtractionPromptBuilder** — testar que o prompt gerado contém schema, contexto e exemplos nas posições corretas. Módulo puro, sem dependências externas.
- **SchemaRegistry** — testar o ciclo de vida completo: criação, adição de campo, deprecação, transição para `validated`, imutabilidade de versões anteriores. Requer PostgreSQL de teste (não mockar).
- **CorrectionProcessor** — testar que uma Correction persiste no PostgreSQL E indexa no Qdrant E evolui o Schema quando há `new_fields`. Requer PostgreSQL + Qdrant de teste.
- **DomainClassifier** — testar os três caminhos: `domain_id` fornecido (confidence 1.0), classificação automática com confidence alta, classificação com confidence baixa (status `needs_confirmation`).

**Módulos a testar via testes de integração (pipeline completo):**

- **ExtractionOrchestrator** — testar o pipeline end-to-end com um PDF real de fixture, verificando que o job transita pelos estados corretos e o resultado no PostgreSQL está íntegro.
- **API Layer** — testar os endpoints críticos: upload, polling de status, submission de Corrections, query de extrações. Verificar enforcement de roles (analyst não pode chamar `POST /domains`).

**Não testar:**
- Implementação interna do prompt (frases exatas) — só o comportamento resultante da extração
- Detalhes de serialização do Qdrant — só o que é recuperado
- Lógica interna do Celery — só o resultado final no PostgreSQL

## Out of Scope

- OCR para PDFs escaneados (sem texto selecionável) — primeira versão assume PDFs com texto extraível
- Crawler automático de sites de ministérios — ingestão é sempre via upload manual
- Reprocessamento automático de jobs antigos quando o Schema evolui — sempre explícito e manual
- Notificações push (email, Slack) quando um job completa — polling via API
- Multi-tenancy — sistema single-tenant na primeira versão
- Exportação de dados extraídos para formatos externos (CSV, Excel) — apenas via API JSON
- Fine-tuning de modelos — aprendizado é exclusivamente via few-shot dinâmico

## Further Notes

- O skill `/register-domain` automatiza o Domain Registration analisando o PDF e propondo os campos para confirmação do admin — reduz o atrito no cold start.
- O skill `/evolve-schema` analisa Corrections acumuladas e sugere campos a adicionar/deprecar, e se o Schema está pronto para `validated` (critério: ≥10 jobs validados, <2 corrections/job, nenhum campo novo recente).
- O skill `/build-extraction-prompt` permite ajuste fino do prompt de extração quando a qualidade de um Domínio cai, sem tocar no código.
- O skill `/update-docs` regenera `docs/ARCHITECTURE.md` com diagramas Mermaid atualizados — deve ser executado após qualquer mudança de componente ou endpoint.
- Decisões arquiteturais com justificativa registradas em [docs/adr/](adr/).
