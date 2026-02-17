"""
This module defines exceptions related to
database operations in the Mwalika Agent
system.
"""

from exceptions.core import ApplicationException


class MongoDBException(ApplicationException):
	"""
	Exception raised for errors related to
	MongoDB operations.
	"""

	pass


class QdrantException(ApplicationException):
	"""
	Exception raised for errors related to
	QuadrantDB operations.
	"""

	pass
