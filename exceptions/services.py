"""
This module defines exceptions related to
external service interactions in the Mwalika Agent
system, such as API calls to third-party services
or internal microservices.
"""

from exceptions.core import ApplicationException


class OpenAIException(ApplicationException):
	"""
	Exception raised for errors related to
	OpenAI API interactions.
	"""

	pass
