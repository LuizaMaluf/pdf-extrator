# sentence-transformers com modelo em português para embeddings

Os embeddings usados para recuperar Few-Shot Examples por similaridade semântica são gerados localmente via sentence-transformers com um modelo treinado em português (ex: `neuralmind/bert-base-portuguese-cased`). Relatórios governamentais brasileiros contêm terminologia técnica específica — orçamentária, epidemiológica, jurídica — que modelos treinados majoritariamente em inglês representam mal. Um modelo PT-BR produz embeddings semanticamente mais precisos para esse domínio, sem custo por chamada e sem dependência de API externa.

**Considered Options**:
- Modelo genérico multilíngue (ex: `paraphrase-multilingual-MiniLM`): mais simples, mas qualidade semântica inferior para jargão técnico brasileiro.
- API de embeddings externa (ex: OpenAI): viola o requisito de ferramentas open source.
