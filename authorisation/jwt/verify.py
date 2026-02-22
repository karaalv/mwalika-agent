"""
This module contains utilities for verifying JWT
tokens for user authorisation.
"""

from os import getenv
from typing import Any

import jwt

from exceptions.authorisation import JwtValidationException

# --- Constants ---

_JWT_SECRET = getenv('JWT_SECRET')

# --- JWT verification utilities ---


def verify_token(token: str, issuer: str, typ: str) -> dict[str, Any]:
	try:
		payload = jwt.decode(
			token,
			_JWT_SECRET,
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

	sub = payload.get('sub')
	if not isinstance(sub, str) or not sub:
		raise JwtValidationException('Missing subject')

	return payload
