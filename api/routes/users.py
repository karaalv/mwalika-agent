"""
This module contains user-related API routes,
this includes user information retrieval,
and other user management functionalities.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request

from api.config.settings import (
	COOKIE_DOMAIN,
	REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
	USER_ID_COOKIE_EXPIRY_SECONDS,
)
from api.dependencies.ratelimit import (
	require_access_and_rate_limit,
	require_frontend_and_rate_limit,
	require_refresh_and_rate_limit,
)
from api.guards.users.routes import (
	guard_at_generation,
	guard_claim_cookie_generation,
	guard_rt_generation,
)
from api.utils.ip_addresses import get_http_ip
from api.utils.responses import http_response
from api.utils.tokens import (
	generate_access_token,
	generate_refresh_token,
	verify_claim_token,
)
from schemas.security.ratelimit import ResourcePolicyType

# --- Router setup ---

users_router = APIRouter()

# --- API routes ---


@users_router.get(
	'/mwalika-rt',
	dependencies=[
		Depends(
			require_frontend_and_rate_limit(
				ResourcePolicyType.ACCESS_TOKEN
			)
		)
	],
)
async def get_refresh_token(
	request: Request,
):
	"""
	An endpoint to provide a general refresh token for the client.
	This token grants access to the agent endpoint which will
	create a new user once a message is sent.
	"""
	request_id = getattr(request.state, 'request_id', '')
	ip = get_http_ip(request)

	# Guard the issuance of the refresh token
	await guard_rt_generation(ip_address=ip)

	# Create a general refresh token with no specific user ID
	token = generate_refresh_token(user_id=None)
	response = http_response(
		request_id=request_id,
		success=True,
		message='General refresh token generated successfully',
	)

	response.set_cookie(
		key='mwalika_rt',
		value=token,
		httponly=True,
		secure=True,
		samesite='lax',
		max_age=REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
		expires=REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
		domain=COOKIE_DOMAIN,
	)
	return response


@users_router.get(
	'/mwalika-at',
)
async def get_access_token(
	request: Request,
	user_id: str = Depends(
		require_refresh_and_rate_limit(
			ResourcePolicyType.ACCESS_TOKEN
		)
	),
):
	"""
	An endpoint to provide a general access token for the client.
	This token can be used to authenticate with the agent endpoint,
	but will not be associated with a user until a message is sent.
	"""
	request_id = getattr(request.state, 'request_id', '')

	# Guard the issuance of the access token
	if user_id:
		await guard_at_generation(user_id=user_id)

	# Create access token and scope to user if
	# user id is in cookie
	token = generate_access_token(user_id=user_id)
	return http_response(
		request_id=request_id,
		success=True,
		message='General access token generated successfully',
		data={'access_token': token},
	)


@users_router.post(
	'/claim-user-cookie',
)
async def claim_cookie(
	request: Request,
	payload: dict[str, Any] = Depends(  # noqa: B008
		require_access_and_rate_limit(  # noqa: B008
			ResourcePolicyType.CLAIM_USER_COOKIE
		)
	),
):
	"""
	An endpoint that allows a client to claim a user ID by providing
	a valid claim token. This sets the user ID in a cookie and issues
	a new refresh token associated with that user ID.
	"""
	request_id = getattr(request.state, 'request_id', '')
	body: dict = await request.json()
	claim_token = body.get('claim_token')
	claim_user_id = body.get('user_id')

	if not claim_token or not claim_user_id:
		return http_response(
			request_id=request_id,
			success=False,
			message=(
				'Missing claim_token or user_id in request body'
			),
			status_code=400,
		)

	# Verify the claim token and ensure it
	# matches the provided user_id
	user_id = payload.get('sub', '')
	token_id = payload.get('jti')

	if not user_id or not token_id:
		return http_response(
			request_id=request_id,
			success=False,
			message='Invalid token payload: missing sub or jti claim',
			status_code=401,
		)

	try:
		payload = verify_claim_token(claim_token)
		if payload.get('sub') != claim_user_id:
			raise ValueError(
				'Claim token user_id does not match provided user_id'
			)

		if user_id != claim_user_id:
			raise ValueError(
				'Claim token user_id does not match '
				'authenticated user_id'
			)
	except Exception as e:
		return http_response(
			request_id=request_id,
			success=False,
			message=f'Invalid claim token: {str(e)}',
			status_code=401,
		)

	# Guard the claiming of the user ID cookie
	await guard_claim_cookie_generation(
		ip_address=get_http_ip(request),
		user_id=user_id,
		token_id=token_id,
	)

	# If the token is valid, set the
	# user ID in the cookies

	response = http_response(
		request_id=request_id,
		success=True,
		message='User ID claimed successfully',
	)

	# Set the user_id cookie
	response.set_cookie(
		key='user_id',
		value=user_id,
		httponly=True,
		secure=True,
		samesite='lax',
		max_age=USER_ID_COOKIE_EXPIRY_SECONDS,
		expires=USER_ID_COOKIE_EXPIRY_SECONDS,
		domain=COOKIE_DOMAIN,
	)

	# Create new refresh token for the user
	new_refresh_token = generate_refresh_token(user_id=user_id)

	response.set_cookie(
		key='mwalika_rt',
		value=new_refresh_token,
		httponly=True,
		secure=True,
		samesite='lax',
		max_age=REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
		expires=REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
		domain=COOKIE_DOMAIN,
	)
	return response
