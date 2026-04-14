from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user
from app.core.database import get_db
from app.models.knowledge import Document, DocumentStatus, KnowledgeBase
from app.models.user import Organization, User
from app.schemas.common import MessageResponse
from app.services.rag_service import rag_service


class DocumentResponse(BaseModel):
	id: UUID
	kb_id: UUID
	filename: str
	file_type: str
	file_size: Optional[int]
	status: str
	chunk_count: int
	error_message: Optional[str]
	created_at: datetime

	class Config:
		from_attributes = True

router = APIRouter()


@router.post("/{agent_id}/upload", response_model=DocumentResponse)
async def upload_document(
	agent_id: UUID,
	file: UploadFile = File(...),
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""Upload a knowledge document and dispatch async RAG processing."""
	_ = current_user
	_ = DocumentStatus

	filename = file.filename or ""
	if "." not in filename:
		raise HTTPException(status_code=400, detail="Invalid file name")

	file_type = filename.rsplit(".", 1)[-1].lower()
	allowed_types = {"pdf", "docx", "txt"}
	if file_type not in allowed_types:
		raise HTTPException(status_code=400, detail="Unsupported file type")

	file_content = await file.read()
	max_size = 50 * 1024 * 1024
	if len(file_content) > max_size:
		raise HTTPException(status_code=400, detail="File too large (max 50MB)")

	kb = await rag_service.get_or_create_kb(db, agent_id, current_org.id)
	document = await rag_service.upload_document(
		db,
		kb,
		file_content,
		filename,
		file_type,
	)
	return document


@router.get("/{agent_id}", response_model=list[DocumentResponse])
async def list_documents(
	agent_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""List all documents for an agent's knowledge base."""
	_ = current_user
	kb = await rag_service.get_or_create_kb(db, agent_id, current_org.id)
	return await rag_service.list_documents(db, kb.id)


@router.delete("/{agent_id}/documents/{doc_id}", response_model=MessageResponse)
async def delete_document(
	agent_id: UUID,
	doc_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""Delete a document and its vectors from the current organization."""
	_ = current_user
	_ = agent_id
	await rag_service.delete_document(db, doc_id, current_org.id)
	return MessageResponse(message="Document deleted")


@router.get("/{agent_id}/documents/{doc_id}/status", response_model=dict)
async def get_document_status(
	agent_id: UUID,
	doc_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""Get processing status for a document in an agent knowledge base."""
	_ = current_user

	result = await db.execute(
		select(Document)
		.join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
		.where(
			Document.id == doc_id,
			KnowledgeBase.agent_id == agent_id,
			KnowledgeBase.org_id == current_org.id,
		)
	)
	document = result.scalar_one_or_none()
	if not document:
		raise HTTPException(status_code=404, detail="Document not found")

	return {
		"doc_id": str(document.id),
		"status": document.status.value if hasattr(document.status, "value") else str(document.status),
		"chunk_count": document.chunk_count,
		"error_message": document.error_message,
	}
