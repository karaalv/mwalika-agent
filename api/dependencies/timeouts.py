"""
This module defines timeouts used with the rate limiting
system of the Mwalika Agent, these timeouts are used to
control how long a client (identified by IP or user ID) is
allowed to queue requests when they exceed their rate limit
before they start getting rejected immediately.
"""

import asyncio
from contextlib import asynccontextmanager

from aiolimiter import AsyncLimiter
from fastapi import (
	HTTPException,
	WebSocket,
	WebSocketException,
	status,
)

from api.config.settings import (
	HTTP_RATE_LIMIT_TIMEOUT_SECONDS,
	WS_HANDSHAKE_RATE_LIMIT_TIMEOUT_SECONDS,
)
from api.websocket.utils import ws_send_error_and_close

# --- Timeout context manager ---


@asynccontextmanager
async def timeout_limiter_http(
	limiter: AsyncLimiter,
	timeout_seconds: float = HTTP_RATE_LIMIT_TIMEOUT_SECONDS,
):
	"""
	Async context manager that attempts to acquire a slot in the
	given limiter within a specified timeout period. If the timeout
	is exceeded, an HTTPException with status code 429 is raised.
	"""
	try:
		await asyncio.wait_for(
			limiter.acquire(), timeout=timeout_seconds
		)
	except asyncio.TimeoutError as e:
		raise HTTPException(
			status_code=status.HTTP_429_TOO_MANY_REQUESTS,
			detail='Rate limit exceeded, please try again later.',
		) from e

	yield


@asynccontextmanager
async def timeout_limiter_ws(
	limiter: AsyncLimiter,
	websocket: WebSocket,
	timeout_seconds: float = WS_HANDSHAKE_RATE_LIMIT_TIMEOUT_SECONDS,
):
	"""
	Async context manager that attempts to acquire a slot in the
	given limiter within a specified timeout period for WebSocket
	connections. If the timeout is exceeded, an error message is sent
	to the client and the connection is closed with a 1013 try again
	later code.
	"""
	try:
		await asyncio.wait_for(
			limiter.acquire(), timeout=timeout_seconds
		)
	except asyncio.TimeoutError as e:
		await ws_send_error_and_close(
			websocket=websocket,
			error_message=(
				'Rate limit exceeded, please try again later.'
			),
			request_id='',
			connection_id='',
		)
		raise WebSocketException(
			code=status.WS_1013_TRY_AGAIN_LATER
		) from e

	yield
