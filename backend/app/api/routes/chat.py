from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_org, get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.user import Organization, User
from app.schemas.chat import ChatMessageRequest, ConversationOut
from app.schemas.common import MessageResponse
from app.services.chat_service import chat_service
from app.services.conversation_service import conversation_service

router = APIRouter()


@router.post("/{agent_id}/stream")
async def stream_chat(
	agent_id: UUID,
	data: ChatMessageRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
) -> StreamingResponse:
	"""Stream assistant response token-by-token as Server-Sent Events."""
	generator = chat_service.stream_chat(
		db,
		agent_id,
		current_user.id,
		current_org.id,
		data.message,
		data.conversation_id,
	)

	return StreamingResponse(
		generator,
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"X-Accel-Buffering": "no",
			"Connection": "keep-alive",
		},
	)


@router.get("/{agent_id}/conversations", response_model=list[ConversationOut])
async def list_conversations(
	agent_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
) -> list[ConversationOut]:
	"""List chat conversations for the current user and agent."""
	_ = current_org
	conversations, _total = await conversation_service.list_conversations(
		db,
		agent_id,
		current_user.id,
	)
	return conversations


@router.get("/{agent_id}/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
	agent_id: UUID,
	conversation_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
) -> ConversationOut:
	"""Get one conversation with all messages."""
	_ = current_org
	result = await db.execute(
		select(Conversation)
		.options(selectinload(Conversation.messages))
		.where(
			Conversation.id == conversation_id,
			Conversation.agent_id == agent_id,
			Conversation.user_id == current_user.id,
		)
	)
	conversation = result.scalar_one_or_none()
	if not conversation:
		raise HTTPException(status_code=404, detail="Conversation not found")
	return conversation


@router.delete("/{agent_id}/conversations/{conversation_id}", response_model=MessageResponse)
async def delete_conversation(
	agent_id: UUID,
	conversation_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
) -> MessageResponse:
	"""Soft delete a conversation by marking its title as deleted."""
	_ = current_org
	result = await db.execute(
		select(Conversation).where(
			Conversation.id == conversation_id,
			Conversation.agent_id == agent_id,
			Conversation.user_id == current_user.id,
		)
	)
	conversation = result.scalar_one_or_none()
	if not conversation:
		raise HTTPException(status_code=404, detail="Conversation not found")

	if hasattr(conversation, "is_active"):
		conversation.is_active = False
	else:
		conversation.title = "[deleted]"

	await db.flush()
	return MessageResponse(message="Conversation deleted")
