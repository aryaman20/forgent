from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user
from app.core.database import get_db
from app.models.user import Organization, User
from app.schemas.agent import AgentCreateRequest, AgentResponse, AgentUpdateRequest
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.agent_service import agent_service

router = APIRouter()


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: AgentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
):
    """Create a new agent in the current organization."""
    agent = await agent_service.create_agent(db, current_org, current_user.id, data)
    return agent


@router.get("", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_org),
):
    """List agents for the current organization with pagination."""
    _ = current_user
    agents, total = await agent_service.list_agents(db, current_org.id, page, page_size)
    return PaginatedResponse[AgentResponse](
        items=agents,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
	agent_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""Get one agent by ID within the current organization."""
	_ = current_user
	return await agent_service.get_agent(db, agent_id, current_org.id)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
	agent_id: UUID,
	data: AgentUpdateRequest,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""Update an existing agent configuration."""
	_ = current_user
	return await agent_service.update_agent(db, agent_id, current_org.id, data)


@router.delete("/{agent_id}", response_model=MessageResponse)
async def delete_agent(
	agent_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	"""Soft delete an agent in the current organization."""
	_ = current_user
	await agent_service.delete_agent(db, agent_id, current_org.id)
	return MessageResponse(message="Agent deleted successfully")
