"""
This module contains the configuration settings
for the MongoDB client. It handles the main client
configuration used across the application.
"""

from os import getenv

from pymongo import AsyncMongoClient

from exceptions.core import ErrorContext
from exceptions.databases import MongoDBException
from shared.logging import LogStyle, cprint

# --- Configuration ---

# Global MongoDB Client
_mongo_client: AsyncMongoClient | None = None

# --- Client Management ---

# Connection management functions


async def start_mongodb_client() -> None:
	"""Initializes the global MongoDB client."""
	global _mongo_client
	if _mongo_client is None:
		mongo_uri = getenv('MONGODB_URI')
		if not mongo_uri:
			raise MongoDBException(
				message=(
					'MONGODB_URI environment variable is not set.'
				),
				code='mongodb_uri_none',
				context=ErrorContext(
					operation='start_mongodb_client',
					component='mongodb.config',
				),
			)

		try:
			cprint(
				'Initializing MongoDB client...',
				style=LogStyle.INFO,
				prefix='mongodb.config',
			)
			_mongo_client = AsyncMongoClient(mongo_uri)
			await _mongo_client.aconnect()
			cprint(
				'MongoDB client initialized.',
				style=LogStyle.SUCCESS,
				prefix='mongodb.config',
			)
		except Exception as e:
			raise MongoDBException(
				message=('Failed to initialize MongoDB client.'),
				code='mongodb_client_init_failed',
				context=ErrorContext(
					operation='start_mongodb_client',
					component='mongodb.config',
				),
				cause=e,
			) from e


async def close_mongodb_client() -> None:
	"""Closes the global MongoDB client."""
	global _mongo_client
	if _mongo_client is not None:
		try:
			cprint(
				'Closing MongoDB client...',
				style=LogStyle.INFO,
				prefix='mongodb.config',
			)
			await _mongo_client.close()
			set_mongodb_client(None)
			cprint(
				'MongoDB client closed.',
				style=LogStyle.SUCCESS,
				prefix='mongodb.config',
			)
		except Exception as e:
			raise MongoDBException(
				message=('Failed to close MongoDB client.'),
				code='mongodb_client_close_failed',
				context=ErrorContext(
					operation='close_mongodb_client',
					component='mongodb.config',
				),
				cause=e,
			) from e


# Client accessors


def get_mongodb_client() -> AsyncMongoClient:
	"""Returns the global MongoDB client."""
	global _mongo_client
	if _mongo_client is None:
		raise MongoDBException(
			message='MongoDB client is not initialized.',
			code='mongodb_client_none',
			context=ErrorContext(
				operation='get_mongodb_client',
				component='mongodb.config',
			),
		)

	return _mongo_client


def set_mongodb_client(
	client: AsyncMongoClient | None,
) -> None:
	"""Sets the global MongoDB client."""
	global _mongo_client
	_mongo_client = client


# Session management functions


async def is_mongodb_connected() -> bool:
	"""Checks if the MongoDB client is connected."""
	client = get_mongodb_client()
	try:
		await client.admin.command('ping')
		return True
	except Exception:
		return False
