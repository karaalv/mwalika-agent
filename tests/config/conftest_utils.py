"""
This module defines utility functions and fixtures
used as part of the test setup for the Mwalika Agent system.
"""

from os import getenv

from openai import AsyncOpenAI
from pymongo import AsyncMongoClient
from qdrant_client import AsyncQdrantClient

from api.lifecycle.maintenance import (
	start_maintenance_tasks,
	stop_maintenance_tasks,
)
from api.lifecycle.websocket_registry import (
	start_websocket_registry,
	stop_websocket_registry,
)
from databases.mongodb.config import (
	close_mongodb_client,
	set_mongodb_client,
)
from databases.qdrant.config import (
	close_qdrant_client,
	set_qdrant_client,
)
from events.lifecycle import (
	start_event_system,
	stop_event_system,
)
from openai_client.config import (
	close_openai_client,
	set_openai_client,
)
from security.lifecycle import (
	start_security_system,
	stop_security_system,
)
from shared.logging import (
	LogStyle,
	cprint,
)
from tests.utils.mongodb import clear_test_databases

# --- Async client setup functions ---


async def init_test_clients() -> None:
	"""
	Initializes async clients for MongoDB, QdrantDB, and OpenAI
	using environment variables for configuration. This function is
	used in test fixtures to set up the necessary clients before
	running tests.
	"""

	await _init_mongo_test_client()
	await _init_qdrant_test_client()
	await _init_openai_test_client()

	# Clear test databases to ensure a
	# clean slate for testing.
	await clear_test_databases()


async def _init_mongo_test_client() -> None:
	mongo_uri = getenv('MONGODB_URI')
	if not mongo_uri:
		raise RuntimeError(
			'MONGODB_URI environment variable is not set.'
		)
	client = AsyncMongoClient(mongo_uri)
	await client.aconnect()
	set_mongodb_client(client)
	cprint(
		'MongoDB test client initialized.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


async def _init_qdrant_test_client() -> None:
	qdrant_url = getenv('QDRANT_URL')
	qdrant_api_key = getenv('QDRANT_API_KEY')
	if not qdrant_url:
		raise RuntimeError(
			'QDRANT_URL environment variable is not set.'
		)
	client = AsyncQdrantClient(
		url=qdrant_url,
		api_key=qdrant_api_key,
	)
	set_qdrant_client(client)
	cprint(
		'QdrantDB test client initialized.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


async def _init_openai_test_client() -> None:
	openai_api_key = getenv('OPENAI_API_KEY')
	if not openai_api_key:
		raise RuntimeError(
			'OPENAI_API_KEY environment variable is not set.'
		)
	client = AsyncOpenAI(api_key=openai_api_key)
	set_openai_client(client)
	cprint(
		'OpenAI test client initialized.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


# --- Async client teardown functions ---


async def close_test_clients() -> None:
	"""
	Closes async clients for MongoDB, QdrantDB, and OpenAI.
	This function is used in test fixtures to clean up resources
	after tests have completed.
	"""

	await close_openai_client()
	await close_qdrant_client()
	await close_mongodb_client()
	cprint(
		'All test clients closed.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


# --- Server lifecycle startup functions ---


async def start_server_clients() -> None:
	"""
	Starts server clients for server specific components,
	note general clients like MongoDB, QdrantDB, and OpenAI are
	started in the main test fixture setup to ensure they are
	available for all tests.
	"""
	await start_security_system()
	start_websocket_registry()
	start_event_system()
	start_maintenance_tasks()


# --- Server lifecycle shutdown functions ---


async def stop_server_clients() -> None:
	"""
	Stops server clients for server specific components,
	note general clients like MongoDB, QdrantDB, and OpenAI are
	stopped in the main test fixture teardown to ensure they are
	available for all tests until the very end.
	"""
	await stop_maintenance_tasks()
	await stop_websocket_registry()
	await stop_event_system()
	await stop_security_system()
