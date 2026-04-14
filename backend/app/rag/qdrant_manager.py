from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    VectorParams,
)
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class QdrantManager:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.vector_size = 1536

    async def get_collection_name(self, org_id: str, agent_id: str) -> str:
        safe_org_id = org_id.replace("-", "_")
        safe_agent_id = agent_id.replace("-", "_")
        return f"org_{safe_org_id}_agent_{safe_agent_id}"

    async def create_collection(self, collection_name: str) -> None:
        try:
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
                optimizers_config=OptimizersConfigDiff(indexing_threshold=20000),
                hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
            )
            logger.info("Qdrant collection created", collection_name=collection_name)
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" in message or "exists" in message:
                logger.warning(
                    "Qdrant collection already exists",
                    collection_name=collection_name,
                )
                return
            logger.exception(
                "Failed to create Qdrant collection",
                collection_name=collection_name,
                error=str(exc),
            )
            raise

    async def delete_collection(self, collection_name: str) -> None:
        try:
            await self.client.delete_collection(collection_name=collection_name)
            logger.info("Qdrant collection deleted", collection_name=collection_name)
        except Exception as exc:
            logger.warning(
                "Failed to delete Qdrant collection",
                collection_name=collection_name,
                error=str(exc),
            )

    async def collection_exists(self, collection_name: str) -> bool:
        try:
            await self.client.get_collection(collection_name=collection_name)
            return True
        except Exception:
            return False

    async def get_collection_stats(self, collection_name: str) -> dict:
        info = await self.client.get_collection(collection_name=collection_name)
        return {
            "collection_name": collection_name,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
        }


qdrant_manager = QdrantManager()
