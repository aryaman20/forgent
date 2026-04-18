from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[UUID] = None
    stream: bool = True


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    tokens_input: int
    tokens_output: int
    latency_ms: int
    sources: list[dict]
    model_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: UUID
    agent_id: UUID
    title: Optional[str]
    created_at: datetime
    messages: list[MessageOut] = []

    class Config:
        from_attributes = True


class StreamChunk(BaseModel):
    type: str
    content: str = ""
    sources: list[dict] = []
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    usage: Optional[dict] = None
