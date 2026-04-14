from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class ToolConfig(BaseModel):
    name: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class RetrievalConfig(BaseModel):
    top_k: int = 5
    strategy: str = "hybrid"
    rerank: bool = True
    score_threshold: float = 0.5


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str = Field(default="You are a helpful assistant.", min_length=10)
    model_provider: ModelProvider = ModelProvider.OPENAI
    model_name: str = "gpt-4o"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=100, le=8000)
    tools_config: list[ToolConfig] = Field(default_factory=list)
    retrieval_config: RetrievalConfig = Field(default_factory=RetrievalConfig)

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str, info):
        """Validate that the selected model belongs to the selected provider."""
        provider = info.data.get("model_provider")
        valid_models = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            "anthropic": ["claude-opus-4-6", "claude-sonnet-4-6"],
            "google": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "ollama": [],
        }
        provider_value = provider.value if hasattr(provider, "value") else provider
        if provider_value and provider_value != "ollama":
            if v not in valid_models.get(provider_value, []):
                raise ValueError(f"Model {v} not valid for provider {provider_value}")
        return v


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model_provider: ModelProvider | None = None
    model_name: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=100, le=8000)
    tools_config: list[ToolConfig] | None = None
    retrieval_config: RetrievalConfig | None = None
    is_active: bool | None = None


class AgentResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: str | None
    system_prompt: str
    model_provider: str
    model_name: str
    temperature: float
    max_tokens: int
    tools_config: list[dict]
    retrieval_config: dict
    has_knowledge_base: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
