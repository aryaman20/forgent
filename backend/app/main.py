import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents, analytics, billing, chat, knowledge
from app.core.config import settings
from app.core.database import engine

logger = structlog.get_logger()


# -- Lifespan -----------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
	logger.info("Starting Forgent API", env=settings.APP_ENV)

	# Set LangSmith env vars for tracing at startup.
	os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
	os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
	os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

	logger.info("LangSmith tracing enabled", project=settings.LANGCHAIN_PROJECT)
	yield

	await engine.dispose()
	logger.info("Forgent API shutdown complete")


# -- App Instance -------------------------------------------------
app = FastAPI(
	title="Forgent API",
	description="Agentic SaaS Platform -- Build and deploy your own AI agents",
	version="1.0.0",
	lifespan=lifespan,
	docs_url="/docs",
	redoc_url="/redoc",
)


# -- CORS Middleware ---------------------------------------------
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.ALLOWED_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


# -- Routes -------------------------------------------------------
app.include_router(
	agents.router,
	prefix=f"{settings.API_V1_PREFIX}/agents",
	tags=["Agents"],
)
app.include_router(
	knowledge.router,
	prefix=f"{settings.API_V1_PREFIX}/knowledge",
	tags=["Knowledge"],
)
app.include_router(
	chat.router,
	prefix=f"{settings.API_V1_PREFIX}/chat",
	tags=["Chat"],
)
app.include_router(
	analytics.router,
	prefix=f"{settings.API_V1_PREFIX}/analytics",
	tags=["Analytics"],
)
app.include_router(
	billing.router,
	prefix=f"{settings.API_V1_PREFIX}/billing",
	tags=["Billing"],
)


@app.get("/health", tags=["Health"])
async def health_check():
	return {
		"status": "healthy",
		"app": settings.APP_NAME,
		"env": settings.APP_ENV,
		"version": "1.0.0",
	}


@app.get("/", tags=["Root"])
async def root():
	return {"message": "Welcome to Forgent API", "docs": "/docs"}
