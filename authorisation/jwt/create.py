"""
This module contains utilities for creating JWT
tokens for user authorisation.
"""

import time
from os import getenv
from typing import Any

import jwt

from shared.ids import generate_uuid_str

# --- Constants ---

_JWT_SECRET = getenv('JWT_SECRET')

# --- JWT creation utilities ---


def create_token(
	sub: str,
	iss: str,
	typ: str,
	ttl_seconds: int = 180,
) -> str:
	now = int(time.time())

	payload: dict[str, Any] = {
		'typ': typ,
		'sub': sub,
		'iss': iss,
		'iat': now,
		'exp': now + ttl_seconds,
		'jti': generate_uuid_str(),
	}

	token = jwt.encode(
		payload,
		_JWT_SECRET,
		algorithm='HS256',
	)

	# PyJWT may return str or bytes depending on
	# version/config, normalise to str.
	if isinstance(token, bytes):
		return token.decode('utf-8')

	return token
