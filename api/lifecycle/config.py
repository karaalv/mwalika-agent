"""
This module contains all lifecycle management utilities
for the API system, including initialization and shutdown
of global components.
"""

from os import getenv

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
	start_mongodb_client,
)
from databases.qdrant.config import (
	close_qdrant_client,
	start_qdrant_client,
)
from events.lifecycle import start_event_system, stop_event_system
from exceptions.api import APIException
from exceptions.core import ErrorContext
from observability.sentry.config import init_sentry
from openai_client.config import (
	close_openai_client,
	start_openai_client,
)
from security.lifecycle import (
	start_security_system,
	stop_security_system,
)

# --- Lifecycle management utilities ---


async def startup() -> None:
	"""Starts up all necessary components for the API system."""
	init_sentry()
	start_websocket_registry()
	start_event_system()
	start_openai_client()
	await start_mongodb_client()
	start_qdrant_client()
	await start_security_system()
	start_maintenance_tasks()


async def shutdown() -> None:
	"""Shuts down all components gracefully."""
	await stop_maintenance_tasks()
	await stop_websocket_registry()
	await stop_event_system()
	await close_openai_client()
	await close_mongodb_client()
	await close_qdrant_client()
	await stop_security_system()
	await stop_maintenance_tasks()


# --- Environment loading ---


def check_environment() -> None:
	"""Checks that the MWALIKA_ENV variable is set correctly."""
	env = getenv('MWALIKA_ENV')
	if env not in ('production', 'testing', 'development'):
		raise APIException(
			message=(
				'Invalid MWALIKA_ENV value. '
				'Must be "production", "testing", '
				'or "development".'
			),
			code='invalid_environment',
			context=ErrorContext(
				operation='check_environment',
				component='api.lifecycle.config',
				metadata={'MWALIKA_ENV': env},
			),
		)

	port = getenv('MWALIKA_SERVER_PORT')
	if port is None or not port.isdigit():
		raise APIException(
			message=(
				'Invalid MWALIKA_SERVER_PORT value. '
				'Must be a valid integer port number.'
			),
			code='invalid_server_port',
			context=ErrorContext(
				operation='check_environment',
				component='api.lifecycle.config',
				metadata={'MWALIKA_SERVER_PORT': port},
			),
		)

	jwt_secret = getenv('JWT_SECRET')
	if not jwt_secret:
		raise APIException(
			message='JWT_SECRET environment variable is not set.',
			code='missing_jwt_secret',
			context=ErrorContext(
				operation='check_environment',
				component='api.lifecycle.config',
				metadata={'JWT_SECRET': jwt_secret},
			),
		)
