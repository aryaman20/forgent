# backend/app/models/agent.py

import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Identity
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # The system prompt is what makes each agent unique.
    system_prompt = Column(Text, nullable=False, default="You are a helpful assistant.")

    # LLM configuration
    model_provider = Column(String(50), default="openai")
    model_name = Column(String(100), default="gpt-4o")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)

    # Tools the agent can use
    tools_config = Column(JSONB, default=list)

    # RAG config
    has_knowledge_base = Column(Boolean, default=False)
    retrieval_config = Column(JSONB, default=dict)

    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)

    organization = relationship("Organization", back_populates="agents")
    knowledge_bases = relationship("KnowledgeBase", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")
