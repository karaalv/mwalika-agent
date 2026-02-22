"""
This module defines exceptions related to user
authorisation in the Mwalika Agent system.
"""


class JwtValidationException(Exception):
	"""Raised when there is an error validating a JWT token."""

	pass
