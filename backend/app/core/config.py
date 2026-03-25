from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	# -- App --------------------------------------------------
	APP_NAME: str = "Forgent"
	APP_ENV: str = "development"
	SECRET_KEY: str
	API_V1_PREFIX: str = "/api/v1"
	ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

	# -- Database ---------------------------------------------
	DATABASE_URL: str  # async postgres URL

	# -- Redis ------------------------------------------------
	REDIS_URL: str = "redis://localhost:6379"

	# -- Qdrant -----------------------------------------------
	QDRANT_URL: str = "http://localhost:6333"
	QDRANT_API_KEY: str | None = None  # None for local

	# -- Clerk Auth -------------------------------------------
	CLERK_SECRET_KEY: str
	CLERK_PUBLISHABLE_KEY: str

	# -- LLM Providers ----------------------------------------
	OPENAI_API_KEY: str
	ANTHROPIC_API_KEY: str
	GOOGLE_API_KEY: str

	# -- LangSmith --------------------------------------------
	LANGCHAIN_API_KEY: str
	LANGCHAIN_TRACING_V2: bool = True
	LANGCHAIN_PROJECT: str = "forgent"

	# -- AWS S3 -----------------------------------------------
	AWS_ACCESS_KEY_ID: str
	AWS_SECRET_ACCESS_KEY: str
	AWS_BUCKET_NAME: str
	AWS_REGION: str = "ap-south-1"

	# -- Stripe -----------------------------------------------
	STRIPE_SECRET_KEY: str = ""
	STRIPE_WEBHOOK_SECRET: str = ""

	class Config:
		env_file = ".env"  # reads from .env file automatically
		case_sensitive = True  # ENV_VAR must match exactly


# lru_cache means this function runs ONCE and caches the result
# so Settings() is not re-created on every request -- important for performance
@lru_cache()
def get_settings() -> Settings:
	return Settings()


# This is the single global settings object used everywhere
settings = get_settings()
