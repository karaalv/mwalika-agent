"""
This module contains utilities for verifying JWT
tokens for user authorisation.
"""

from typing import Any

import jwt

from exceptions.authorisation import JwtValidationException

# --- JWT verification utilities ---


def verify_token(
	token: str,
	issuer: str,
	typ: str,
	secret: str,
) -> dict[str, Any]:
	try:
		payload = jwt.decode(
			token,
			secret,
			algorithms=['HS256'],
			issuer=issuer,
			options={
				'require': [
					'exp',
					'iat',
					'sub',
					'typ',
					'iss',
				],
			},
		)
	except jwt.ExpiredSignatureError as e:
		raise JwtValidationException('Token expired') from e
	except jwt.InvalidTokenError as e:
		raise JwtValidationException('Invalid token') from e

	if payload.get('typ') != typ:
		raise JwtValidationException('Wrong token type')

	if payload.get('iss') != issuer:
		raise JwtValidationException('Wrong token issuer')

	return payload
