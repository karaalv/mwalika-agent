"""
This module contains user-related API routes,
this includes user information retrieval,
and other user management functionalities.
"""

from fastapi import APIRouter, Request

from api.config.settings import (
	COOKIE_DOMAIN,
	USER_ID_COOKIE_EXPIRY_SECONDS,
)
from api.utils.responses import http_response
from authorisation.jwt.verify import verify_token

# --- Router setup ---

users_router = APIRouter()

# --- API routes ---


@users_router.post('/claim-user-cookie')
async def claim_cookie(request: Request):
	"""
	An endpoint to verify the claim token sent by the client,
	and set the user ID in the cookies if the token is valid.
	"""
	request_id = getattr(request.state, 'request_id', '')
	body: dict = await request.json()
	claim_token = body.get('claim_token')
	user_id = body.get('user_id')

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
