"""
This module defines dependencies related to authentication
and authorization for the Mwalika Agent API, such as
token validation and user identification.
"""

from fastapi import Header, HTTPException, Request, status

from authorisation.jwt.verify import verify_token


def verify_refresh_token(request: Request):
	"""
	Dependency to verify the refresh token from cookies.
	Validates the token and returns the user ID if valid.
	"""
	refresh_token = request.cookies.get('mwalika_rt')
	if not refresh_token:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail='Refresh token missing',
		)
	try:
		payload = verify_token(
			token=refresh_token, issuer='mwalika-agent', typ='refresh'
		)
		# TODO: Check for block status, etc. here as well if needed
		return payload  # Return the token payload
	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=str(e),
		) from e


def verify_access_header(
	request: Request, authorization: str | None = Header(...)
):
	"""
	Dependency to verify the Authorization header
	for protected endpoints. Expects a Bearer token and
	validates it as an access token.
	"""
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
		# TODO: Check for block status, etc. here as well if needed
		return payload  # Return the token payload
	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=str(e),
		) from e


def verify_frontend_header(
	request: Request, x_mwalika: str | None = Header(...)
):
	"""
	Dependency to verify the presence of a custom header
	that indicates the request is coming from the frontend.
	This can be used for additional security checks or
	to apply specific logic for frontend requests.
	"""
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
		# TODO: Check for block status, etc. here as well if needed
		return payload  # Return the token payload
	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail=str(e),
		) from e
