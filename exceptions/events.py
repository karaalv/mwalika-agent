"""
This module defines exceptions related
to events in the Mwalika Agent system.
"""

from exceptions.core import ApplicationException


class EventBusException(ApplicationException):
	"""
	Exception raised for errors related to
	the EventBus operations.
	"""

	pass


class EventForwarderException(ApplicationException):
	"""
	Exception raised for errors related to
	the EventForwarder operations.
	"""

	pass
