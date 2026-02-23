"""
This module contains user-related API routes,
this includes user information retrieval,
and other user management functionalities.
"""

from fastapi import APIRouter, Depends, Request

from api.config.settings import (
	ACCESS_TOKEN_EXPIRY_SECONDS,
	COOKIE_DOMAIN,
	REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
	USER_ID_COOKIE_EXPIRY_SECONDS,
)
from api.dependencies.ratelimit import (
	require_access_and_rate_limit,
	require_refresh_and_rate_limit,
)
from api.utils.responses import http_response
from authorisation.jwt.create import create_token
from authorisation.jwt.verify import verify_token
from schemas.security.ratelimit import ResourcePolicyType

# --- Router setup ---

users_router = APIRouter()

# --- API routes ---


@users_router.get('/mwalika-rt')
async def get_general_refresh_token(request: Request):
	"""
	An endpoint to provide a general refresh token for the client.
	This token grants access to the agent endpoint which will
	create a new user once a message is sent.
	"""
	request_id = getattr(request.state, 'request_id', '')
	# Create a general refresh token with no specific user ID
	token = create_token(
		sub='',
		iss='mwalika-agent',
		typ='refresh',
		ttl_seconds=REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
	)
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
async def get_general_access_token(
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
	mwalika_rt = request.cookies.get('mwalika_rt')
	if not mwalika_rt:
		return http_response(
			request_id=request_id,
			success=False,
			message='No refresh token found in cookies',
			status_code=401,
		)

	# Verify the refresh token before issuing an access token
	try:
		verify_token(
			token=mwalika_rt,
			issuer='mwalika-agent',
			typ='refresh',
		)
	except Exception as e:
		return http_response(
			request_id=request_id,
			success=False,
			message=f'Invalid refresh token: {str(e)}',
			status_code=401,
		)

	# Create access token and scope to user if
	# user id is in cookie
	token = create_token(
		sub=user_id if user_id else '',
		iss='mwalika-agent',
		typ='access',
		ttl_seconds=ACCESS_TOKEN_EXPIRY_SECONDS,
	)
	# TODO: Track token usage with user id
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
	user_id: str = Depends(
		require_access_and_rate_limit(
			ResourcePolicyType.CLAIM_USER_COOKIE
		)
	),
):
	"""
	An endpoint to verify the claim token sent by the client,
	and set the user ID in the cookies if the token is valid.
	"""
	request_id = getattr(request.state, 'request_id', '')
	body: dict = await request.json()
	claim_token = body.get('claim_token')

	if not claim_token or not user_id:
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
	try:
		payload = verify_token(
			token=claim_token,
			issuer='mwalika-agent',
			typ='claim',
		)
		if payload.get('user_id') != user_id:
			raise ValueError(
				'Token user_id does not match provided user_id'
			)
	except Exception as e:
		return http_response(
			request_id=request_id,
			success=False,
			message=f'Invalid claim token: {str(e)}',
			status_code=401,
		)

	# If the token is valid, set the user ID in the cookies

	# TODO: Begin tracking tokens for user
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
	return response
