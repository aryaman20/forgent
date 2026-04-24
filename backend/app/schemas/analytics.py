from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UsageEventOut(BaseModel):
    id: UUID
    org_id: UUID
    agent_id: Optional[UUID]
    event_type: str
    model: Optional[str]
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    created_at: datetime

    class Config:
        from_attributes = True


class DailyUsageStat(BaseModel):
    date: str
    total_messages: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float


class AgentUsageStat(BaseModel):
    agent_id: UUID
    agent_name: str
    total_messages: int
    total_tokens: int
    total_cost_usd: float


class AnalyticsSummary(BaseModel):
    period_days: int
    total_messages: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    avg_latency_ms: float
    daily_stats: list[DailyUsageStat]
    agent_stats: list[AgentUsageStat]
    top_model: Optional[str]


class BillingInfo(BaseModel):
    plan: str
    status: str
    current_period_end: Optional[datetime]
    agent_count: int
    agent_limit: int
    message_count_today: int
    message_limit_daily: int
