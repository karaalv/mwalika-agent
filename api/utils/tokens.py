"""
This module contains utility functions for API
token management used across the API routes and related
components.
"""

from os import getenv

from pydantic import BaseModel, Field

from api.config.settings import (
	ACCESS_TOKEN_EXPIRY_SECONDS,
	FRONTEND_TOKEN_EXPIRY_SECONDS,
	REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
)
from authorisation.jwt.create import create_token
from authorisation.jwt.verify import verify_token
from shared.time import get_timestamp_s

# --- Schemas and types ---


class TokenResponse(BaseModel):
	token: str = Field(..., description='The JWT token string')
	expires_at_ms: int = Field(
		...,
		description=(
			'The expiration timestamp '
			'of the token in milliseconds '
			'since epoch'
		),
	)


# --- Constants ---

_TOKEN_ISS = 'mwalika-agent-api'


def _get_secret(type: str) -> str:
	if type == 'jwt':
		return getenv('JWT_SECRET', '')
	elif type == 'frontend':
		return getenv('FRONTEND_SECRET', '')
	else:
		raise ValueError(f'Unknown secret type: {type}')


# --- Frontend token management utilities ---


def generate_frontend_token() -> str:
	"""
	Generates a frontend token, which can be used to authenticate
	requests from the frontend to protected API endpoints in the
	Mwalika Agent API.
	"""
	frontend_token = create_token(
		sub='frontend',
		iss=_TOKEN_ISS,
		typ='frontend',
		ttl_seconds=FRONTEND_TOKEN_EXPIRY_SECONDS,
		secret=_get_secret('frontend'),
	)
	return frontend_token


def verify_frontend_token(token: str) -> dict:
	"""
	Verifies a frontend token to ensure it is valid and was issued
	for the frontend. This can be used in dependencies to protect
	API endpoints that should only be accessed by the frontend.
	"""
	payload = verify_token(
		token=token,
		issuer=_TOKEN_ISS,
		typ='frontend',
		secret=_get_secret('frontend'),
	)
	return payload


# --- Refresh token management utilities ---


def generate_refresh_token(user_id: str | None = None) -> str:
	"""
	Generates a refresh token for the given user ID, which can be
	used to obtain new access tokens and manage user sessions in the
	Mwalika Agent API.
	"""
	refresh_token = create_token(
		sub=user_id or '',
		iss=_TOKEN_ISS,
		typ='refresh',
		ttl_seconds=REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS,
		secret=_get_secret('jwt'),
	)
	return refresh_token


def verify_refresh_token(token: str) -> dict:
	"""
	Verifies a refresh token to ensure it is valid and was issued
	for the Mwalika Agent API. This can be used in dependencies to
	protect API endpoints that require a valid refresh token.
	"""
	payload = verify_token(
		token=token,
		issuer=_TOKEN_ISS,
		typ='refresh',
		secret=_get_secret('jwt'),
	)
	return payload


# --- Access token management utilities ---


def generate_access_token(
	user_id: str | None = None,
) -> TokenResponse:
	"""
	Generates an access token for the given user ID, which can be
	used to authenticate API requests and manage user sessions in the
	Mwalika Agent API.
	"""
	access_token = create_token(
		sub=user_id or '',
		iss=_TOKEN_ISS,
		typ='access',
		ttl_seconds=ACCESS_TOKEN_EXPIRY_SECONDS,
		secret=_get_secret('jwt'),
	)

	# Get the expiration timestamp in milliseconds since epoch
	expires_at_ms = (
		get_timestamp_s() + ACCESS_TOKEN_EXPIRY_SECONDS
	) * 1000
	return TokenResponse(
		token=access_token,
		expires_at_ms=expires_at_ms,
	)


def verify_access_token(token: str) -> dict:
	"""
	Verifies an access token to ensure it is valid and was issued
	for the Mwalika Agent API. This can be used in dependencies to
	protect API endpoints that require a valid access token.
	"""
	payload = verify_token(
		token=token,
		issuer=_TOKEN_ISS,
		typ='access',
		secret=_get_secret('jwt'),
	)
	return payload


# --- Claim token management utilities ---


def generate_claim_token(user_id: str) -> str:
	"""
	Generates a claim token for the given user ID, which can be
	used to claim a user ID by providing a valid claim token. This
	sets the user ID in a cookie and issues a new refresh token
	associated with that user ID.
	"""
	claim_token = create_token(
		sub=user_id,
		iss=_TOKEN_ISS,
		typ='claim',
		secret=_get_secret('jwt'),
	)
	return claim_token


def verify_claim_token(token: str) -> dict:
	"""
	Verifies a claim token to ensure it is valid and was issued
	for the Mwalika Agent API. This can be used in dependencies to
	protect API endpoints that require a valid claim token.
	"""
	payload = verify_token(
		token=token,
		issuer=_TOKEN_ISS,
		typ='claim',
		secret=_get_secret('jwt'),
	)
	return payload
