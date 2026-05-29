from functools import lru_cache

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from app.settings import settings

EMBEDDING_DIM = 768  # neuralmind/bert-base-portuguese-cased


@lru_cache(maxsize=1)
def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        prefer_grpc=True,
    )


async def ensure_collections() -> None:
    client = get_qdrant_client()

    for name in ("domain_signatures", "few_shot_examples"):
        if not await client.collection_exists(name):
            await client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )

    # payload index obrigatório para filtered search por domain_id
    for collection in ("domain_signatures", "few_shot_examples"):
        await client.create_payload_index(
            collection_name=collection,
            field_name="domain_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
