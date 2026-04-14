import asyncio

import structlog
from langchain_core.documents import Document

from app.rag.chunker import document_chunker
from app.rag.embedder import embedding_service
from app.rag.qdrant_manager import qdrant_manager
from app.rag.retriever import RetrievalConfig, retriever

logger = structlog.get_logger()


class RAGPipeline:
	async def ingest_document(
		self,
		file_path: str,
		file_type: str,
		collection_name: str,
		doc_id: str,
		filename: str,
	) -> dict:
		_ = (asyncio, Document)

		# Step 1: Ensure collection exists
		exists = await qdrant_manager.collection_exists(collection_name)
		if not exists:
			await qdrant_manager.create_collection(collection_name)

		# Step 2: Process and chunk document
		metadata = {
			"doc_id": doc_id,
			"filename": filename,
			"file_type": file_type,
		}
		chunks = await document_chunker.process_file(file_path, file_type, metadata)

		# Step 3: Embed and store chunks
		stored_count = await embedding_service.store_chunks(chunks, collection_name, doc_id)

		logger.info(
			"Document ingestion complete",
			doc_id=doc_id,
			chunk_count=stored_count,
			collection_name=collection_name,
		)

		return {
			"doc_id": doc_id,
			"chunk_count": stored_count,
			"collection_name": collection_name,
			"status": "completed",
		}

	async def delete_document(self, collection_name: str, doc_id: str) -> None:
		await embedding_service.delete_doc_chunks(collection_name, doc_id)
		logger.info(
			"Document vectors deleted",
			collection_name=collection_name,
			doc_id=doc_id,
		)

	async def query(
		self,
		query_text: str,
		collection_name: str,
		config: RetrievalConfig = None,
	) -> list[dict]:
		return await retriever.retrieve(query_text, collection_name, config)

	async def build_context(self, results: list[dict], max_tokens: int = 3000) -> str:
		max_chars = max_tokens * 4
		current_chars = 0
		parts: list[str] = []

		for i, result in enumerate(results):
			text = result.get("text", "")
			entry = f"[Source {i + 1}]: {text}\n"
			if current_chars + len(entry) > max_chars:
				break
			parts.append(entry)
			current_chars += len(entry)

		return "".join(parts)


rag_pipeline = RAGPipeline()
