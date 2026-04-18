from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageRole

logger = structlog.get_logger()


class ConversationService:
    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        agent_id: UUID,
        user_id: UUID,
        conversation_id: UUID = None,
    ) -> Conversation:
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conversation.agent_id != agent_id:
                raise HTTPException(status_code=400, detail="Conversation agent mismatch")
            return conversation

        conversation = Conversation(agent_id=agent_id, user_id=user_id, title=None)
        db.add(conversation)
        await db.flush()
        logger.info(
            "Conversation created",
            conversation_id=str(conversation.id),
            agent_id=str(agent_id),
            user_id=str(user_id),
        )
        return conversation

    async def get_conversation_history(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        limit: int = 20,
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        latest_messages = result.scalars().all()
        return list(reversed(latest_messages))

    async def save_message(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        latency_ms: int = 0,
        sources: list = None,
        model_used: str = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            sources=sources or [],
            model_used=model_used,
        )
        db.add(message)
        await db.flush()
        return message

    async def update_conversation_title(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        first_message: str,
    ) -> None:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        title_base = (first_message or "").strip()
        conversation.title = (title_base[:50] + "...") if title_base else "New conversation..."
        await db.flush()

    async def list_conversations(
        self,
        db: AsyncSession,
        agent_id: UUID,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        offset = (page - 1) * page_size

        total = await db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.agent_id == agent_id,
                Conversation.user_id == user_id,
            )
        )

        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.agent_id == agent_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        conversations = result.scalars().all()
        return list(conversations), total or 0

    def build_messages_for_llm(self, history: list[Message]) -> list[dict]:
        return [{"role": msg.role.value, "content": msg.content} for msg in history]


conversation_service = ConversationService()
