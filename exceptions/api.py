"""
This module defines exceptions related to API
operations in the Mwalika Agent system.
"""

from exceptions.core import ApplicationException


class APIException(ApplicationException):
	"""
	Exception raised for errors related to API
	operations, such as request validation failures,
	authentication errors, or internal server errors.
	"""

	pass


class WebSocketException(APIException):
	"""
	Exception raised for errors related to WebSocket
	operations, such as connection issues, message
	processing errors, or protocol violations.
	"""

	pass


class WebSocketRegistryException(APIException):
	"""
	Exception raised for errors related to the
	WebSocketRegistry, such as registration failures,
	connection management errors, or message sending
	failures.
	"""

	pass
