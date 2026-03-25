from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_clerk_token
from app.models.user import Organization, User

# Extracts Bearer token from Authorization header.
bearer_scheme = HTTPBearer()


async def get_current_user(
	credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
	db: AsyncSession = Depends(get_db),
) -> User:
	"""
	Core auth dependency:
	1) extract JWT
	2) verify with Clerk
	3) find user by clerk_id
	4) return User model
	"""
	token = credentials.credentials
	payload = await verify_clerk_token(token)

	clerk_id = payload.get("sub")
	if not clerk_id:
		raise HTTPException(status_code=401, detail="Invalid token payload")

	result = await db.execute(select(User).where(User.clerk_id == clerk_id))
	user = result.scalar_one_or_none()

	if not user:
		raise HTTPException(
			status_code=404,
			detail="User not found. Please complete onboarding.",
		)

	if not user.is_active:
		raise HTTPException(status_code=403, detail="Account disabled")

	return user


async def get_current_org(
	current_user: User = Depends(get_current_user),
	db: AsyncSession = Depends(get_db),
) -> Organization:
	"""
	Gets the organization for the current user.
	All tenant-scoped queries should use this org.
	"""
	result = await db.execute(
		select(Organization).where(Organization.id == current_user.org_id)
	)
	org = result.scalar_one_or_none()

	if not org:
		raise HTTPException(status_code=404, detail="Organization not found")

	return org


async def get_current_context(
	current_user: User = Depends(get_current_user),
	current_org: Organization = Depends(get_current_org),
):
	return {"user": current_user, "org": current_org}
