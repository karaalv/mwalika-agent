"""
This module defines settings used for configuring
properties of the Mwalika Agent API such as rate limits,
cookie settings, and other relevant configuration parameters.
"""

from os import getenv

# Cookie settings

COOKIE_DOMAIN = getenv('COOKIE_DOMAIN')
USER_ID_COOKIE_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days
