# backend/app/models/knowledge.py

import enum
import uuid

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"  # just uploaded, not processed yet
    PROCESSING = "processing"  # worker is chunking + embedding
    COMPLETED = "completed"  # vectors are ready for RAG
    FAILED = "failed"  # processing failed


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)

    # Format: org_{org_id}_agent_{agent_id}
    qdrant_collection = Column(String(255), nullable=False)

    agent = relationship("Agent", back_populates="knowledge_bases")
    documents = relationship("Document", back_populates="knowledge_base")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False)

    filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, url
    file_size = Column(Integer, nullable=True)  # bytes
    s3_key = Column(String(500), nullable=True)  # path in S3

    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
