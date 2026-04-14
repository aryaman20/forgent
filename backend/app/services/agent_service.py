from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_agent_graph
from app.models.agent import Agent
from app.models.user import Organization
from app.schemas.agent import AgentCreateRequest, AgentUpdateRequest

logger = structlog.get_logger()


class AgentService:
    async def create_agent(
        self,
        db: AsyncSession,
        org: Organization,
        user_id: UUID,
        data: AgentCreateRequest,
    ) -> Agent:
        agent_count = await db.scalar(
            select(func.count(Agent.id)).where(
                Agent.org_id == org.id,
                Agent.is_active.is_(True),
            )
        )

        org_plan = org.plan.value if hasattr(org.plan, "value") else org.plan
        if org_plan == "free" and (agent_count or 0) >= 3:
            raise HTTPException(
                status_code=403,
                detail="Free plan limit: 3 agents. Upgrade to Pro for unlimited agents.",
            )

        agent = Agent(
            org_id=org.id,
            created_by=user_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            model_provider=data.model_provider.value,
            model_name=data.model_name,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            tools_config=[tool.model_dump() for tool in data.tools_config],
            retrieval_config=data.retrieval_config.model_dump(),
        )
        db.add(agent)
        await db.flush()

        logger.info("Agent created", agent_id=str(agent.id), org_id=str(org.id))
        return agent

    async def get_agent(self, db: AsyncSession, agent_id: UUID, org_id: UUID) -> Agent:
        result = await db.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.org_id == org_id,
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    async def list_agents(
        self,
        db: AsyncSession,
        org_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Agent], int]:
        offset = (page - 1) * page_size

        total = await db.scalar(
            select(func.count(Agent.id)).where(
                Agent.org_id == org_id,
                Agent.is_active.is_(True),
            )
        )

        result = await db.execute(
            select(Agent)
            .where(Agent.org_id == org_id, Agent.is_active.is_(True))
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        agents = result.scalars().all()
        return agents, total or 0

    async def update_agent(
        self,
        db: AsyncSession,
        agent_id: UUID,
        org_id: UUID,
        data: AgentUpdateRequest,
    ) -> Agent:
        agent = await self.get_agent(db, agent_id, org_id)

        for field, value in data.dict(exclude_none=True).items():
            setattr(agent, field, value)

        await db.flush()
        return agent

    async def delete_agent(self, db: AsyncSession, agent_id: UUID, org_id: UUID) -> None:
        agent = await self.get_agent(db, agent_id, org_id)
        agent.is_active = False
        await db.flush()

    def get_agent_graph(self, agent: Agent):
        return build_agent_graph(
            provider=agent.model_provider,
            model_name=agent.model_name,
            temperature=agent.temperature,
            system_prompt=agent.system_prompt,
            tools_config=agent.tools_config or [],
        )


agent_service = AgentService()
