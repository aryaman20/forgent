from uuid import UUID

import boto3
import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.agent import Agent
from app.models.knowledge import Document, DocumentStatus, KnowledgeBase
from app.rag.embedder import embedding_service
from app.rag.qdrant_manager import qdrant_manager
from app.workers.tasks import process_document_task

logger = structlog.get_logger()


class RAGService:
	async def get_or_create_kb(
		self,
		db: AsyncSession,
		agent_id: UUID,
		org_id: UUID,
	) -> KnowledgeBase:
		result = await db.execute(
			select(KnowledgeBase).where(
				KnowledgeBase.agent_id == agent_id,
				KnowledgeBase.org_id == org_id,
			)
		)
		kb = result.scalar_one_or_none()
		if kb:
			return kb

		agent_result = await db.execute(
			select(Agent).where(
				Agent.id == agent_id,
				Agent.org_id == org_id,
			)
		)
		agent = agent_result.scalar_one_or_none()
		if not agent:
			raise HTTPException(status_code=404, detail="Agent not found")

		collection_name = await qdrant_manager.get_collection_name(str(org_id), str(agent_id))
		await qdrant_manager.create_collection(collection_name)

		kb = KnowledgeBase(
			agent_id=agent_id,
			org_id=org_id,
			name=f"KB for agent {agent_id}",
			qdrant_collection=collection_name,
		)
		agent.has_knowledge_base = True
		db.add(kb)
		await db.flush()
		return kb

	async def upload_document(
		self,
		db: AsyncSession,
		kb: KnowledgeBase,
		file_content: bytes,
		filename: str,
		file_type: str,
	) -> Document:
		s3 = boto3.client(
			"s3",
			aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
			aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
			region_name=settings.AWS_REGION,
		)
		s3_key = f"orgs/{kb.org_id}/agents/{kb.agent_id}/docs/{filename}"
		s3.put_object(
			Bucket=settings.AWS_BUCKET_NAME,
			Key=s3_key,
			Body=file_content,
		)

		doc = Document(
			kb_id=kb.id,
			filename=filename,
			file_type=file_type,
			s3_key=s3_key,
			file_size=len(file_content),
			status=DocumentStatus.PENDING,
		)
		db.add(doc)
		await db.flush()

		process_document_task.delay(
			document_id=str(doc.id),
			s3_key=s3_key,
			file_type=file_type,
			collection_name=kb.qdrant_collection,
			filename=filename,
		)

		logger.info(
			"Document processing task dispatched",
			document_id=str(doc.id),
			kb_id=str(kb.id),
			s3_key=s3_key,
		)
		return doc

	async def update_document_status(
		self,
		db: AsyncSession,
		doc_id: UUID,
		status: DocumentStatus,
		chunk_count: int = 0,
		error: str = None,
	) -> None:
		result = await db.execute(select(Document).where(Document.id == doc_id))
		doc = result.scalar_one_or_none()
		if not doc:
			raise HTTPException(status_code=404, detail="Document not found")

		doc.status = status
		doc.chunk_count = chunk_count
		doc.error_message = error
		await db.flush()

	async def list_documents(self, db: AsyncSession, kb_id: UUID) -> list[Document]:
		result = await db.execute(
			select(Document)
			.where(Document.kb_id == kb_id)
			.order_by(Document.created_at.desc())
		)
		return list(result.scalars().all())

	async def delete_document(self, db: AsyncSession, doc_id: UUID, org_id: UUID) -> None:
		result = await db.execute(
			select(Document, KnowledgeBase)
			.join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
			.where(
				Document.id == doc_id,
				KnowledgeBase.org_id == org_id,
			)
		)
		row = result.first()
		if not row:
			raise HTTPException(status_code=404, detail="Document not found")

		doc, kb = row
		await embedding_service.delete_doc_chunks(kb.qdrant_collection, str(doc.id))
		await db.delete(doc)
		await db.flush()

		logger.info(
			"Document deleted",
			document_id=str(doc.id),
			org_id=str(org_id),
			collection_name=kb.qdrant_collection,
		)


rag_service = RAGService()
