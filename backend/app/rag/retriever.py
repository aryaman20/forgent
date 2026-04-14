import asyncio
from dataclasses import dataclass

import cohere
import structlog
from qdrant_client.models import FieldCondition, Filter, MatchValue, SearchRequest

from app.core.config import settings
from app.rag.embedder import embedding_service
from app.rag.qdrant_manager import qdrant_manager

logger = structlog.get_logger()


@dataclass
class RetrievalConfig:
	top_k: int = 5
	strategy: str = "hybrid"  # "semantic", "hybrid"
	rerank: bool = True
	score_threshold: float = 0.5


class Retriever:
	def __init__(self):
		self.cohere_client = cohere.AsyncClient(
			api_key=getattr(settings, "COHERE_API_KEY", "")
		)

	async def semantic_search(
		self,
		query_vector: list[float],
		collection_name: str,
		top_k: int,
		score_threshold: float,
		doc_id_filter: str = None,
	) -> list[dict]:
		query_filter = None
		if doc_id_filter:
			query_filter = Filter(
				must=[
					FieldCondition(
						key="doc_id",
						match=MatchValue(value=doc_id_filter),
					)
				]
			)

		results = await qdrant_manager.client.search(
			collection_name=collection_name,
			query_vector=query_vector,
			limit=top_k * 2,
			score_threshold=score_threshold,
			with_payload=True,
			query_filter=query_filter,
		)

		return [
			{
				"text": (point.payload or {}).get("text", ""),
				"metadata": (point.payload or {}).get("metadata", {}),
				"score": point.score,
				"point_id": str(point.id),
			}
			for point in results
		]

	async def keyword_search(
		self,
		query: str,
		collection_name: str,
		top_k: int,
	) -> list[dict]:
		_ = SearchRequest
		points, _ = await qdrant_manager.client.scroll(
			collection_name=collection_name,
			scroll_filter=Filter(
				must=[
					FieldCondition(
						key="text",
						match=MatchValue(value=query),
					)
				]
			),
			limit=top_k,
			with_payload=True,
		)

		return [
			{
				"text": (point.payload or {}).get("text", ""),
				"metadata": (point.payload or {}).get("metadata", {}),
				"score": 1.0,
				"point_id": str(point.id),
			}
			for point in points
		]

	async def hybrid_search(
		self,
		query: str,
		query_vector: list[float],
		collection_name: str,
		config: RetrievalConfig,
	) -> list[dict]:
		semantic_results, keyword_results = await asyncio.gather(
			self.semantic_search(
				query_vector=query_vector,
				collection_name=collection_name,
				top_k=config.top_k,
				score_threshold=config.score_threshold,
			),
			self.keyword_search(
				query=query,
				collection_name=collection_name,
				top_k=config.top_k,
			),
		)

		merged: dict[str, dict] = {}
		for item in semantic_results + keyword_results:
			point_id = item["point_id"]
			if point_id not in merged or item["score"] > merged[point_id]["score"]:
				merged[point_id] = item

		deduped = sorted(merged.values(), key=lambda r: r["score"], reverse=True)
		return deduped[: config.top_k]

	async def rerank(self, query: str, results: list[dict], top_k: int) -> list[dict]:
		if not getattr(settings, "COHERE_API_KEY", "") or not results:
			return results[:top_k]

		texts = [item["text"] for item in results]
		rerank_response = await self.cohere_client.rerank(
			model="rerank-english-v3.0",
			query=query,
			documents=texts,
			top_n=top_k,
		)

		reranked: list[dict] = []
		for item in rerank_response.results:
			selected = dict(results[item.index])
			selected["score"] = float(item.relevance_score)
			reranked.append(selected)
		return reranked

	async def retrieve(
		self,
		query: str,
		collection_name: str,
		config: RetrievalConfig = None,
	) -> list[dict]:
		config = config or RetrievalConfig()
		query_vector = await embedding_service.embed_query(query)

		if config.strategy == "hybrid":
			results = await self.hybrid_search(
				query=query,
				query_vector=query_vector,
				collection_name=collection_name,
				config=config,
			)
		else:
			results = await self.semantic_search(
				query_vector=query_vector,
				collection_name=collection_name,
				top_k=config.top_k,
				score_threshold=config.score_threshold,
			)

		if config.rerank:
			results = await self.rerank(query=query, results=results, top_k=config.top_k)

		logger.info(
			"Retrieval completed",
			strategy=config.strategy,
			result_count=len(results),
		)
		return results


retriever = Retriever()
