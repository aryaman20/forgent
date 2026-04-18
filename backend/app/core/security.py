import base64

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

def _build_clerk_jwks_urls() -> list[str]:
	"""Build candidate Clerk JWKS URLs from configured publishable key."""
	urls: list[str] = []
	publishable_key = (settings.CLERK_PUBLISHABLE_KEY or "").strip()

	if publishable_key.startswith("pk_"):
		parts = publishable_key.split("_", 2)
		if len(parts) == 3 and parts[2]:
			encoded = parts[2]
			encoded += "=" * (-len(encoded) % 4)
			try:
				decoded = base64.b64decode(encoded).decode("utf-8").rstrip("$")
				if decoded:
					urls.append(f"https://{decoded}/.well-known/jwks.json")
			except Exception:
				pass

	# Fallbacks for older Clerk setups.
	urls.append("https://api.clerk.com/v1/jwks")
	urls.append("https://api.clerk.dev/v1/jwks")

	# Keep order but remove duplicates.
	unique_urls: list[str] = []
	for url in urls:
		if url not in unique_urls:
			unique_urls.append(url)
	return unique_urls


async def verify_clerk_token(token: str) -> dict:
	"""
	Verifies a JWT token issued by Clerk.
	Returns the decoded payload.
	Raises 401 if token is invalid or expired.
	"""
	try:
		import jwt

		# Fetch Clerk's public keys used to verify token signature.
		jwks = None
		last_error: Exception | None = None
		async with httpx.AsyncClient(timeout=10.0) as client:
			for jwks_url in _build_clerk_jwks_urls():
				try:
					response = await client.get(jwks_url)
					response.raise_for_status()
					data = response.json()
					if isinstance(data, dict) and isinstance(data.get("keys"), list):
						jwks = data
						break
				except Exception as exc:
					last_error = exc

		if not jwks:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Token verification failed",
			) from last_error

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
