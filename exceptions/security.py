"""
This module defines exceptions related to security
operations in the Mwalika Agent system.
"""

from exceptions.core import ApplicationException


class SecurityServiceException(ApplicationException):
	"""
	Exception raised for errors related to security
	operations, such as authentication failures, access
	denied errors, or security policy violations.
	"""

	pass
