from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user
from app.core.database import get_db
from app.models.agent import Agent
from app.models.user import Organization
from app.schemas.analytics import (
	AgentUsageStat,
	AnalyticsSummary,
	BillingInfo,
	DailyUsageStat,
)
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
	days: int = Query(default=30, ge=1, le=90),
	db: AsyncSession = Depends(get_db),
	current_user=Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	_ = current_user
	return await analytics_service.get_full_analytics(db, current_org.id, days)


@router.get("/daily", response_model=list[DailyUsageStat])
async def get_daily_stats(
	days: int = Query(default=30, ge=1, le=90),
	db: AsyncSession = Depends(get_db),
	current_user=Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	_ = current_user
	return await analytics_service.get_daily_stats(db, current_org.id, days)


@router.get("/agents", response_model=list[AgentUsageStat])
async def get_agent_stats(
	db: AsyncSession = Depends(get_db),
	current_user=Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	_ = current_user
	return await analytics_service.get_agent_stats(db, current_org.id)


@router.get("/billing-info", response_model=BillingInfo)
async def get_billing_info(
	db: AsyncSession = Depends(get_db),
	current_user=Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	_ = current_user

	plan = getattr(current_org.plan, "value", str(current_org.plan))
	limits = {
		"free": {"agent_limit": 3, "message_limit_daily": 100},
		"pro": {"agent_limit": 999, "message_limit_daily": 10000},
		"team": {"agent_limit": 999, "message_limit_daily": 100000},
	}
	applied_limits = limits.get(plan, limits["free"])

	agent_count_query = select(func.count(Agent.id)).where(Agent.org_id == current_org.id)
	agent_count = int((await db.scalar(agent_count_query)) or 0)
	message_count_today = await analytics_service.get_today_message_count(db, current_org.id)

	return BillingInfo(
		plan=plan,
		status="active",
		current_period_end=None,
		agent_count=agent_count,
		agent_limit=applied_limits["agent_limit"],
		message_count_today=message_count_today,
		message_limit_daily=applied_limits["message_limit_daily"],
	)
