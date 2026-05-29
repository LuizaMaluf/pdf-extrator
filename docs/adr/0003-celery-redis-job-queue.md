# Celery + Redis para processamento assíncrono de Extraction Jobs

Extraction Jobs são processados de forma assíncrona (upload retorna job_id, cliente faz polling). Escolhemos Celery + Redis em vez de uma fila implementada no próprio Postgres porque o pipeline vai crescer em complexidade: reprocessamento manual com Schema Version diferente, retries em falha da Claude API, e potencial encadeamento de tarefas (classificação → extração determinística → LLM). Celery suporta tudo isso nativamente com monitoramento via Flower. Uma fila no Postgres seria suficiente hoje, mas exigiria reimplementar essas features manualmente à medida que o sistema crescer.

**Considered Options**:
- Fila no Postgres (pg_notify + tabela de jobs): elimina dependência de Redis, mas sem suporte nativo a retries, prioridades e task chaining.
- RQ (Redis Queue): mais simples que Celery, mas limitado para pipelines com múltiplos estágios.
