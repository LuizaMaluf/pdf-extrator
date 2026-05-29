# Qdrant como vector store para Few-Shot Examples

Few-Shot Examples precisam ser recuperados por similaridade semântica filtrada por Domínio. Escolhemos Qdrant em vez de pgvector (extensão do Postgres) porque Qdrant suporta filtragem por metadata nativamente na busca vetorial — sem isso, seria necessário buscar todos os vetores e filtrar em memória. pgvector eliminaria uma dependência, mas degrada em performance quando a coleção cresce e não oferece filtragem eficiente por campo.

**Considered Options**:
- pgvector: elimina dependência extra (já temos Postgres), mas filtragem por Domínio é ineficiente e performance cai com volume.
- ChromaDB: mais simples, mas menos maduro para produção e sem suporte robusto a filtragem por metadata.
