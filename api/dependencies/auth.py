"""
This module defines dependencies related to authentication
and authorization for the Mwalika Agent API, such as
token validation and user identification.
"""

from dependencies.utils import (
	check_at_blocked,
	check_ip_blocked,
	check_rt_blocked,
	check_user_blocked,
)
from fastapi import (
	Header,
	HTTPException,
	Request,
	WebSocket,
	WebSocketException,
	status,
)

from api.dependencies.timeouts import (
	timeout_limiter_http,
	timeout_limiter_ws,
)
from api.utils.ip_addresses import get_http_ip, get_ws_ip
from api.websocket.utils import ws_send_error_and_close
from authorisation.jwt.verify import verify_token
from schemas.security.ratelimit import ResourcePolicyType
from security.lifecycle import (
	is_at_blocked,
	is_ip_blocked,
	is_user_blocked,
	update_latest_at_request,
	update_latest_ip_request,
	update_latest_user_request,
)
from security.ratelimit.store import get_limiter


async def require_frontend_header(
	request: Request, x_mwalika: str | None = Header(...)
):
	"""
	Dependency to verify the presence of a custom header
	that indicates the request is coming from the frontend.
	This can be used for additional security checks or
	to apply specific logic for frontend requests.
	"""
	ip = get_http_ip(request)

	# Check if the IP is blocked
	await check_ip_blocked(ip)

	# Rate limit auth dependencies based on IP
	limiter = get_limiter(
		policy_type=ResourcePolicyType.API_DEPENDENCY,
		identifier_type='ip',
		identifier_value=ip,
	)
	async with timeout_limiter_http(limiter):
		if x_mwalika != 'frontend':
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail='Invalid X-Mwalika header',
			)
		token = x_mwalika
		try:
			payload = verify_token(
				token=token, issuer='mwalika-agent', typ='frontend'
			)
			# Return the token payload
			return payload
		except Exception as e:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail=str(e),
			) from e


async def require_refresh_token(request: Request):
	"""
	Dependency to verify the refresh token from cookies.
	Validates the token and returns the user ID if valid.
	"""
	refresh_token = request.cookies.get('mwalika_rt')
	ip = get_http_ip(request)

	# Check if the IP is blocked
	await check_ip_blocked(ip)

	# Rate limit auth dependencies based on IP
	limiter = get_limiter(
		policy_type=ResourcePolicyType.API_DEPENDENCY,
		identifier_type='ip',
		identifier_value=ip,
	)
	async with timeout_limiter_http(limiter):
		if not refresh_token:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail='Refresh token missing',
			)
		try:
			payload = verify_token(
				token=refresh_token,
				issuer='mwalika-agent',
				typ='refresh',
			)
			# Check if the refresh token is blocked
			await check_rt_blocked(payload['jti'])

			# If the user has been set in rt, check if
			# the user is blocked as well
			user_id = payload.get('sub')
			if user_id:
				await check_user_blocked(user_id)

			# Return the token payload
			return payload
		except Exception as e:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail=str(e),
			) from e


async def require_access_header(
	request: Request, authorization: str | None = Header(...)
):
	"""
	Dependency to verify the Authorization header
	for protected endpoints. Expects a Bearer token and
	validates it as an access token.
	"""
	ip = get_http_ip(request)

	# Check if the IP is blocked
	await check_ip_blocked(ip)

	# Rate limit auth dependencies based on IP
	limiter = get_limiter(
		policy_type=ResourcePolicyType.API_DEPENDENCY,
		identifier_type='ip',
		identifier_value=ip,
	)
	async with timeout_limiter_http(limiter):
		if not authorization:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail='Authorization header missing',
			)
		if not authorization.startswith('Bearer '):
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail='Invalid authorization header format',
			)
		token = authorization[len('Bearer ') :]
		try:
			payload = verify_token(
				token=token, issuer='mwalika-agent', typ='access'
			)

			# Check if the access token is blocked
			await check_at_blocked(payload['jti'])

			# Check if the user is blocked as well
			user_id = payload.get('sub')
			if user_id:
				await check_user_blocked(user_id)

			# Return the token payload
			return payload
		except Exception as e:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail=str(e),
			) from e


async def ws_require_access_token(websocket: WebSocket):
	"""
	Dependency to verify the access token from query parameters
	for WebSocket connections. Validates the token and returns
	the user ID if valid.
	"""
	ip = get_ws_ip(websocket)
	await update_latest_ip_request(ip)

	# Check if the IP is blocked
	block = await is_ip_blocked(ip)
	if block:
		await ws_send_error_and_close(
			websocket=websocket,
			error_message=block.reason,
			request_id='',
			connection_id='',
		)
		raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

	# Rate limit auth dependencies based on IP
	limiter = get_limiter(
		policy_type=ResourcePolicyType.API_DEPENDENCY,
		identifier_type='ip',
		identifier_value=ip,
	)
	async with timeout_limiter_ws(limiter, websocket):
		# Attempt to get user ID from verified access token payload
		access_token = websocket.query_params.get('access_token')
		if not access_token:
			# If no access token is provided,
			# connect to send error message and
			# close the connection
			await ws_send_error_and_close(
				websocket=websocket,
				error_message='Access token missing',
				request_id='',
				connection_id='',
			)
			raise WebSocketException(
				code=status.WS_1008_POLICY_VIOLATION
			)

		try:
			payload = verify_token(
				token=access_token,
				issuer='mwalika-agent',
				typ='access',
			)
			user_id: str = payload.get('sub', '')
			token_id: str = payload.get('jti', '')

			# Check if the access token is blocked
			await update_latest_at_request(token_id)
			block = await is_at_blocked(token_id)
			if block:
				await ws_send_error_and_close(
					websocket=websocket,
					error_message=block.reason,
					request_id='',
					connection_id='',
				)
				raise WebSocketException(
					code=status.WS_1008_POLICY_VIOLATION
				)

			# Check if the user is blocked as well
			if user_id:
				await update_latest_user_request(user_id)
				block = await is_user_blocked(user_id)
				if block:
					await ws_send_error_and_close(
						websocket=websocket,
						error_message=block.reason,
						request_id='',
						connection_id='',
					)
					raise WebSocketException(
						code=status.WS_1008_POLICY_VIOLATION
					)

			# Return token payload
			return payload
		except Exception as e:
			# If token verification fails,
			# send error message and close connection
			await ws_send_error_and_close(
				websocket=websocket,
				error_message='Invalid access token',
				request_id='',
				connection_id='',
			)
			raise WebSocketException(
				code=status.WS_1008_POLICY_VIOLATION
			) from e
