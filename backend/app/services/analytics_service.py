import asyncio
from datetime import datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import Date, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.analytics import UsageEvent

logger = structlog.get_logger()

MODEL_COSTS = {
	"gpt-4o": {"input": 0.005, "output": 0.015},
	"gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
	"claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
	"claude-opus-4-6": {"input": 0.015, "output": 0.075},
	"gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
	"gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
}


class AnalyticsService:
	def calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
		pricing = MODEL_COSTS.get(model)
		if not pricing:
			return 0.0

		cost = ((tokens_input / 1000.0) * pricing["input"]) + ((tokens_output / 1000.0) * pricing["output"])
		return round(cost, 8)

	async def log_event(
		self,
		db: AsyncSession,
		org_id: UUID,
		agent_id: UUID,
		event_type: str,
		model: str,
		tokens_input: int,
		tokens_output: int,
		latency_ms: int,
		metadata: dict = None,
	) -> None:
		cost_usd = self.calculate_cost(model, tokens_input, tokens_output)

		event = UsageEvent(
			org_id=org_id,
			agent_id=agent_id,
			event_type=event_type,
			model=model,
			tokens_input=tokens_input,
			tokens_output=tokens_output,
			cost_usd=cost_usd,
			latency_ms=latency_ms,
			event_metadata=metadata or {},
		)
		db.add(event)

	async def get_summary(
		self,
		db: AsyncSession,
		org_id: UUID,
		days: int = 30,
	) -> dict:
		since = datetime.utcnow() - timedelta(days=days)

		query = select(
			func.count(UsageEvent.id),
			func.coalesce(func.sum(UsageEvent.tokens_input), 0),
			func.coalesce(func.sum(UsageEvent.tokens_output), 0),
			func.coalesce(func.sum(UsageEvent.cost_usd), 0.0),
			func.coalesce(func.avg(UsageEvent.latency_ms), 0.0),
		).where(
			and_(
				UsageEvent.org_id == org_id,
				UsageEvent.created_at >= since,
			)
		)

		result = await db.execute(query)
		total_messages, total_tokens_input, total_tokens_output, total_cost_usd, avg_latency_ms = result.one()

		return {
			"period_days": days,
			"total_messages": int(total_messages or 0),
			"total_tokens_input": int(total_tokens_input or 0),
			"total_tokens_output": int(total_tokens_output or 0),
			"total_cost_usd": float(total_cost_usd or 0.0),
			"avg_latency_ms": float(avg_latency_ms or 0.0),
			"daily_stats": [],
			"agent_stats": [],
			"top_model": None,
		}

	async def get_daily_stats(
		self,
		db: AsyncSession,
		org_id: UUID,
		days: int = 30,
	) -> list[dict]:
		since = datetime.utcnow() - timedelta(days=days)
		usage_date = cast(UsageEvent.created_at, Date)

		query = (
			select(
				usage_date.label("usage_date"),
				func.count(UsageEvent.id).label("total_messages"),
				func.coalesce(func.sum(UsageEvent.tokens_input + UsageEvent.tokens_output), 0).label("total_tokens"),
				func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("total_cost_usd"),
				func.coalesce(func.avg(UsageEvent.latency_ms), 0.0).label("avg_latency_ms"),
			)
			.where(
				and_(
					UsageEvent.org_id == org_id,
					UsageEvent.created_at >= since,
				)
			)
			.group_by(usage_date)
			.order_by(usage_date.asc())
		)

		rows = (await db.execute(query)).all()

		return [
			{
				"date": row.usage_date.isoformat(),
				"total_messages": int(row.total_messages or 0),
				"total_tokens": int(row.total_tokens or 0),
				"total_cost_usd": float(row.total_cost_usd or 0.0),
				"avg_latency_ms": float(row.avg_latency_ms or 0.0),
			}
			for row in rows
		]

	async def get_agent_stats(
		self,
		db: AsyncSession,
		org_id: UUID,
		days: int = 30,
	) -> list[dict]:
		since = datetime.utcnow() - timedelta(days=days)

		query = (
			select(
				Agent.id.label("agent_id"),
				Agent.name.label("agent_name"),
				func.count(UsageEvent.id).label("total_messages"),
				func.coalesce(func.sum(UsageEvent.tokens_input + UsageEvent.tokens_output), 0).label("total_tokens"),
				func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("total_cost_usd"),
			)
			.join(Agent, UsageEvent.agent_id == Agent.id)
			.where(
				and_(
					UsageEvent.org_id == org_id,
					UsageEvent.created_at >= since,
				)
			)
			.group_by(Agent.id, Agent.name)
			.order_by(func.count(UsageEvent.id).desc())
		)

		rows = (await db.execute(query)).all()

		return [
			{
				"agent_id": row.agent_id,
				"agent_name": row.agent_name,
				"total_messages": int(row.total_messages or 0),
				"total_tokens": int(row.total_tokens or 0),
				"total_cost_usd": float(row.total_cost_usd or 0.0),
			}
			for row in rows
		]

	async def get_full_analytics(
		self,
		db: AsyncSession,
		org_id: UUID,
		days: int = 30,
	) -> dict:
		since = datetime.utcnow() - timedelta(days=days)

		summary, daily_stats, agent_stats = await asyncio.gather(
			self.get_summary(db, org_id, days),
			self.get_daily_stats(db, org_id, days),
			self.get_agent_stats(db, org_id, days),
		)

		top_model_query = (
			select(UsageEvent.model, func.count(UsageEvent.id).label("usage_count"))
			.where(
				and_(
					UsageEvent.org_id == org_id,
					UsageEvent.created_at >= since,
					UsageEvent.model.is_not(None),
				)
			)
			.group_by(UsageEvent.model)
			.order_by(func.count(UsageEvent.id).desc())
			.limit(1)
		)
		top_model_row = (await db.execute(top_model_query)).first()

		summary["daily_stats"] = daily_stats
		summary["agent_stats"] = agent_stats
		summary["top_model"] = top_model_row[0] if top_model_row else None

		logger.info(
			"Analytics summary generated",
			org_id=str(org_id),
			days=days,
			total_messages=summary["total_messages"],
		)
		return summary

	async def get_today_message_count(self, db: AsyncSession, org_id: UUID) -> int:
		today = datetime.utcnow().date()

		query = select(func.count(UsageEvent.id)).where(
			and_(
				UsageEvent.org_id == org_id,
				cast(UsageEvent.created_at, Date) == today,
			)
		)
		count = await db.scalar(query)
		return int(count or 0)


analytics_service = AnalyticsService()
