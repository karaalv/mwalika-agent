"""
This module defines settings used for configuring
properties of the Mwalika Agent API such as rate limits,
cookie settings, and other relevant configuration parameters.
"""

from os import getenv

# Cookie settings

COOKIE_DOMAIN = getenv('COOKIE_DOMAIN')
FRONTEND_TOKEN_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days
USER_ID_COOKIE_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days
REFRESH_TOKEN_COOKIE_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days
ACCESS_TOKEN_EXPIRY_SECONDS = 60 * 5  # 5 minutes

# Rate limit settings

HTTP_RATE_LIMIT_TIMEOUT_SECONDS = 0.1
WS_HANDSHAKE_RATE_LIMIT_TIMEOUT_SECONDS = 0.05
WS_MESSAGE_RATE_LIMIT_TIMEOUT_SECONDS = 0.1
