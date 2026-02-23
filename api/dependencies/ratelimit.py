"""
This module defines dependencies related to rate
limiting for the Mwalika Agent API routes, including
functions to retrieve the appropriate rate limiter based on
the type of resource being accessed and the identifier
(e.g., IP or user ID).
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request

from api.dependencies.auth import (
	verify_access_header,
	verify_refresh_token,
)
from security.ratelimit.policies import ResourcePolicyType
from security.ratelimit.store import get_limiter

# --- Rate limit dependency factory ---


def rate_limit_ip(
	policy_type: ResourcePolicyType,
) -> Callable:
	"""
	Factory function that creates a dependency function for
	rate limiting based on the client's IP address. The
	returned dependency can be used as a FastAPI dependency
	to enforce rate limits on API routes.
	"""

	async def limiter_dependency(request: Request):
		request_ip = (
			request.client.host if request.client else 'unknown'
		)

		limiter = get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		# Attempt to acquire a slot in the limiter,
		# which will enforce the rate limit
		async with limiter:
			return

	return limiter_dependency


def require_refresh_and_rate_limit(
	policy_type: ResourcePolicyType,
) -> Callable:
	"""
	Factory function that creates a dependency function for
	rate limiting based on the user's refresh token. The
	returned dependency first verifies the refresh token to
	identify the user, and then applies the appropriate rate
	limit based on the user ID. If no valid user ID is found,
	it falls back to IP-based rate limiting.
	"""

	async def limiter_dependency(
		request: Request,
		payload: dict[str, Any] = Depends(verify_refresh_token),  # noqa: B008
	):
		# Attempt to get user ID from verified refresh token payload
		user_id = payload.get('sub', '')
		request_ip = (
			request.client.host if request.client else 'unknown'
		)

		# Get limiters for both user ID and IP address
		ip_limiter = get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		if user_id:
			user_limiter = get_limiter(
				policy_type=policy_type,
				identifier_type='user',
				identifier_value=user_id,
			)
			# If user ID is available,
			# apply both user and IP limiters
			async with user_limiter:
				async with ip_limiter:
					return user_id

		# If no user ID, apply only IP limiter
		async with ip_limiter:
			return ''

	return limiter_dependency


def require_access_and_rate_limit(
	policy_type: ResourcePolicyType,
) -> Callable:
	"""
	Factory function that creates a dependency function for
	rate limiting based on the user's access token. The
	returned dependency first verifies the access token to
	identify the user, and then applies the appropriate rate
	limit based on the user ID. If no valid user ID is found,
	it falls back to IP-based rate limiting.
	"""

	async def limiter_dependency(
		request: Request,
		payload: dict[str, Any] = Depends(verify_access_header),  # noqa: B008
	):
		# Attempt to get user ID from verified access token payload
		user_id = payload.get('sub', '')
		request_ip = (
			request.client.host if request.client else 'unknown'
		)

		# Get limiters for both user ID and IP address
		ip_limiter = get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		if user_id:
			user_limiter = get_limiter(
				policy_type=policy_type,
				identifier_type='user',
				identifier_value=user_id,
			)
			# If user ID is available,
			# apply both user and IP limiters
			async with user_limiter:
				async with ip_limiter:
					return user_id

		# If no user ID, apply only IP limiter
		async with ip_limiter:
			return ''

	return limiter_dependency
