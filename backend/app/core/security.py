import httpx
from fastapi import HTTPException, status

from app.core.config import settings

# Clerk's public key endpoint -- used to verify JWT signatures.
CLERK_JWKS_URL = "https://api.clerk.dev/v1/jwks"


async def verify_clerk_token(token: str) -> dict:
	"""
	Verifies a JWT token issued by Clerk.
	Returns the decoded payload.
	Raises 401 if token is invalid or expired.
	"""
	try:
		import jwt

		# Fetch Clerk's public keys used to verify token signature.
		async with httpx.AsyncClient(timeout=10.0) as client:
			response = await client.get(CLERK_JWKS_URL)
			response.raise_for_status()
			jwks = response.json()

		# Get the key from JWKS that matches this token's kid header.
		headers = jwt.get_unverified_header(token)
		public_key = None

		for key in jwks["keys"]:
			if key["kid"] == headers.get("kid"):
				public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
				break

		if not public_key:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Invalid token: key not found",
			)

		payload = jwt.decode(
			token,
			public_key,
			algorithms=["RS256"],
			options={"verify_aud": False},
		)
		return payload

	except HTTPException:
		raise
	except Exception as exc:
		import jwt

		if isinstance(exc, jwt.ExpiredSignatureError):
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Token expired",
			)
		if isinstance(exc, jwt.InvalidTokenError):
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail=f"Invalid token: {str(exc)}",
			)
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Token verification failed",
		)


_ = settings
