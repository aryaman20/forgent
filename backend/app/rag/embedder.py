import asyncio
import uuid

import structlog
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from qdrant_client.http import models as rest
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from app.core.config import settings
from app.rag.qdrant_manager import qdrant_manager

logger = structlog.get_logger()


class EmbeddingService:
	def __init__(self):
		self.embeddings = OpenAIEmbeddings(
			model="text-embedding-3-small",
			api_key=settings.OPENAI_API_KEY,
		)
		self.batch_size = 100

	async def embed_texts(self, texts: list[str]) -> list[list[float]]:
		if not texts:
			return []

		batches = [texts[i : i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
		tasks = [self.embeddings.aembed_documents(batch) for batch in batches]
		results = await asyncio.gather(*tasks)

		vectors: list[list[float]] = []
		for idx, batch_vectors in enumerate(results, start=1):
			logger.info(
				"Embedding batch completed",
				batch_index=idx,
				total_batches=len(results),
				vector_count=len(batch_vectors),
			)
			vectors.extend(batch_vectors)

		return vectors

	async def embed_query(self, query: str) -> list[float]:
		return await self.embeddings.aembed_query(query)

	async def store_chunks(self, chunks: list[Document], collection_name: str, doc_id: str) -> int:
		if not chunks:
			return 0

		texts = [chunk.page_content for chunk in chunks]
		vectors = await self.embed_texts(texts)

		points: list[PointStruct] = []
		for chunk, vector in zip(chunks, vectors):
			points.append(
				PointStruct(
					id=str(uuid.uuid4()),
					vector=vector,
					payload={
						"text": chunk.page_content,
						"metadata": chunk.metadata,
						"doc_id": doc_id,
					},
				)
			)

		for i in range(0, len(points), 100):
			batch = points[i : i + 100]
			await qdrant_manager.client.upsert(
				collection_name=collection_name,
				points=batch,
			)

		logger.info(
			"Document chunks stored",
			collection_name=collection_name,
			doc_id=doc_id,
			points_stored=len(points),
		)
		return len(points)

	async def delete_doc_chunks(self, collection_name: str, doc_id: str) -> None:
		await qdrant_manager.client.delete(
			collection_name=collection_name,
			points_selector=rest.FilterSelector(
				filter=Filter(
					must=[
						FieldCondition(
							key="doc_id",
							match=MatchValue(value=doc_id),
						)
					]
				)
			),
		)
		logger.info(
			"Document chunks deleted",
			collection_name=collection_name,
			doc_id=doc_id,
		)


embedding_service = EmbeddingService()
