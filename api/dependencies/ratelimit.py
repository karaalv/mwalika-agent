"""
This module defines dependencies related to rate
limiting for the Mwalika Agent API routes, including
functions to retrieve the appropriate rate limiter based on
the type of resource being accessed and the identifier
(e.g., IP or user ID).
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request, WebSocket

from api.dependencies.auth import (
	require_access_header,
	require_frontend_header,
	require_refresh_token,
	ws_require_access_token,
)
from api.dependencies.timeouts import (
	timeout_limiter_http,
	timeout_limiter_ws,
)
from api.dependencies.utils import (
	check_ip_blocked,
)
from api.utils.ip_addresses import get_http_ip, get_ws_ip
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
		request_ip = get_http_ip(request)

		# Check if the IP is blocked
		await check_ip_blocked(request_ip)

		limiter = await get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		# Attempt to acquire a slot in the limiter,
		# which will enforce the rate limit
		async with timeout_limiter_http(limiter):
			return

	return limiter_dependency


def require_frontend_and_rate_limit(
	policy_type: ResourcePolicyType,
) -> Callable:
	"""
	Factory function that creates a dependency function for
	rate limiting based on the presence of a valid frontend
	header. This is used to apply rate limits to requests that
	originate from the frontend, identified by a specific header.
	"""

	async def limiter_dependency(
		request: Request,
		payload: dict[str, Any] = Depends(require_frontend_header),  # noqa: B008
	):
		request_ip = get_http_ip(request)

		limiter = await get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		# Attempt to acquire a slot in the limiter,
		# which will enforce the rate limit
		async with timeout_limiter_http(limiter):
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
		payload: dict[str, Any] = Depends(require_refresh_token),  # noqa: B008
	):
		# Attempt to get user ID from verified refresh token payload
		user_id = payload.get('sub', '')
		request_ip = get_http_ip(request)

		# Get limiters for both user ID and IP address
		ip_limiter = await get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		if user_id:
			user_limiter = await get_limiter(
				policy_type=policy_type,
				identifier_type='user',
				identifier_value=user_id,
			)
			# If user ID is available,
			# apply both user and IP limiters
			async with timeout_limiter_http(ip_limiter):
				async with timeout_limiter_http(user_limiter):
					return user_id

		# If no user ID, apply only IP limiter
		async with timeout_limiter_http(ip_limiter):
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
		payload: dict[str, Any] = Depends(require_access_header),  # noqa: B008
	):
		# Attempt to get user ID from verified access token payload
		user_id = payload.get('sub', '')
		request_ip = get_http_ip(request)

		# Get limiters for both user ID and IP address
		ip_limiter = await get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		if user_id:
			user_limiter = await get_limiter(
				policy_type=policy_type,
				identifier_type='user',
				identifier_value=user_id,
			)
			# If user ID is available,
			# apply both user and IP limiters
			async with timeout_limiter_http(ip_limiter):
				async with timeout_limiter_http(user_limiter):
					return payload

		# If no user ID, apply only IP limiter
		async with timeout_limiter_http(ip_limiter):
			return payload

	return limiter_dependency


def ws_require_access_and_rate_limit(
	policy_type: ResourcePolicyType,
) -> Callable:
	"""
	Factory function that creates a dependency function for
	rate limiting based on the user's access token for WebSocket
	endpoints. The returned dependency first verifies the access
	token to identify the user, and then applies the appropriate
	rate limit based on the user ID. If no valid user ID is found,
	it falls back to IP-based rate limiting.
	"""

	async def limiter_dependency(
		websocket: WebSocket,
		payload: dict[str, Any] = Depends(ws_require_access_token),  # noqa: B008
	):
		request_ip = get_ws_ip(websocket)
		user_id = payload.get('sub', '')

		# Get limiters for both user ID and IP address
		ip_limiter = await get_limiter(
			policy_type=policy_type,
			identifier_type='ip',
			identifier_value=request_ip,
		)

		if user_id:
			user_limiter = await get_limiter(
				policy_type=policy_type,
				identifier_type='user',
				identifier_value=user_id,
			)
			# If user ID is available,
			# apply both user and IP limiters
			async with timeout_limiter_ws(ip_limiter, websocket):
				async with timeout_limiter_ws(
					user_limiter, websocket
				):
					return payload

		# If no user ID, apply only IP limiter
		async with timeout_limiter_ws(ip_limiter, websocket):
			return payload

	return limiter_dependency
