# backend/app/models/user.py

import enum
import uuid

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin


class UserRole(str, enum.Enum):
    OWNER = "owner"  # created the org, full access
    ADMIN = "admin"  # can manage agents + members
    MEMBER = "member"  # can use agents only


class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


# Organization = one company/team (multi-tenancy unit).
# All data in Forgent is scoped to an org.
class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)  # URL-friendly name
    plan = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)

    users = relationship("User", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True)

    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", back_populates="users")
