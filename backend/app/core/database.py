from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# -- Engine -------------------------------------------------------
# The engine is the core connection to your database.
# Async engine means queries do not block your server.
# While waiting for DB response, FastAPI can handle other requests.
engine = create_async_engine(
	settings.DATABASE_URL,
	echo=settings.APP_ENV == "development",  # logs SQL in dev, silent in prod
	pool_size=10,  # keep 10 connections open (connection pool)
	max_overflow=20,  # allow 20 extra connections at peak traffic
	pool_pre_ping=True,  # test connection before using (handles dropped connections)
)

# -- Session Factory ----------------------------------------------
# Like a factory that creates database sessions on demand.
# Each API request gets its own session -- important for isolation.
AsyncSessionLocal = async_sessionmaker(
	engine,
	class_=AsyncSession,
	expire_on_commit=False,  # avoids extra queries right after commit
)


# -- Base Model ---------------------------------------------------
# All database models should inherit from this base.
class Base(DeclarativeBase):
	pass


# -- Common Timestamp Mixin --------------------------------------
# Reuse created_at and updated_at fields across models.
class TimestampMixin:
	created_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),  # DB sets this automatically on insert
		nullable=False,
	)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),  # DB updates this automatically on every update
		nullable=False,
	)


# -- Dependency ---------------------------------------------------
# FastAPI dependency that provides one DB session per request.
async def get_db() -> AsyncSession:
	async with AsyncSessionLocal() as session:
		try:
			yield session
			await session.commit()
		except Exception:
			await session.rollback()
			raise
