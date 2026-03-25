# backend/app/models/analytics.py

import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base, TimestampMixin


# Every LLM call gets logged here. This powers analytics dashboards.
class UsageEvent(Base, TimestampMixin):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    event_type = Column(String(50), nullable=False)

    # LLM cost tracking
    model = Column(String(100), nullable=True)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)

    # "metadata" is a reserved Declarative attribute, so map to a safe field name.
    event_metadata = Column("metadata", JSONB, default=dict)
