"""
This module contains lifecycle utilities for the websocket
registry and its components (singletons, background tasks, etc).
"""

import sentry_sdk
from fastapi import WebSocket

from api.websocket.registry import WebSocketRegistry
from exceptions.api import WebSocketRegistryException
from exceptions.core import ErrorContext
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.api.responses import WebSocketResponse
from shared.logging import LogStyle, cprint

# --- Global instances ---

_websocket_registry: WebSocketRegistry | None = None

# --- Helpers ---


def _raise_registry_not_initialized(op: str) -> None:
	add_breadcrumb(
		category='api.lifecycle',
		message='WebSocket registry is not initialized.',
		level=BreadcrumbLevel.ERROR,
		data={
			'operation': op,
		},
	)
	exception = WebSocketRegistryException(
		message='WebSocket registry is not initialized.',
		code='websocket_registry_none',
		context=ErrorContext(
			operation=op,
			component='api.lifecycle',
		),
	)
	sentry_sdk.capture_exception(exception)
	raise exception


# --- Lifecycle management ---


def start_websocket_registry() -> None:
	"""Initializes the global WebSocket registry."""
	global _websocket_registry
	if _websocket_registry is None:
		_websocket_registry = WebSocketRegistry()
		cprint(
			'WebSocket registry initialized.',
			style=LogStyle.SUCCESS,
			prefix='api.lifecycle',
		)


async def stop_websocket_registry() -> None:
	"""Closes the global WebSocket registry."""
	global _websocket_registry
	if _websocket_registry is not None:
		await _websocket_registry.close_all_connections(
			reason='Server shutdown'
		)
		_websocket_registry = None
		cprint(
			'WebSocket registry closed.',
			style=LogStyle.SUCCESS,
			prefix='api.lifecycle',
		)


# --- Accessors and mutators ---


def set_websocket_registry(
	registry: WebSocketRegistry | None,
) -> None:
	"""Sets the global WebSocket registry (for testing)."""
	global _websocket_registry
	_websocket_registry = registry


def get_websocket_registry(
	op: str = 'get_websocket_registry',
) -> WebSocketRegistry:
	"""Returns the global WebSocket registry."""
	global _websocket_registry
	if _websocket_registry is None:
		_raise_registry_not_initialized(op)
		raise  # Unreachable --- for type checker
	return _websocket_registry


# --- Main lifecycle functions ---

# Connection management functions


async def add_websocket_connection(
	user_id: str, connection_id: str, websocket: WebSocket
):
	"""Adds a new WebSocket connection to the registry."""
	# Exceptions handled in WebSocketRegistry
	registry = get_websocket_registry(op='add_websocket_connection')
	await registry.add_connection(user_id, connection_id, websocket)


async def remove_websocket_connection(
	user_id: str, connection_id: str, reason: str = 'Normal closure'
):
	"""Removes a WebSocket connection from the registry."""
	# Exceptions handled in WebSocketRegistry
	registry = get_websocket_registry(
		op='remove_websocket_connection'
	)
	await registry.remove_connection(
		user_id, connection_id, reason=reason
	)


# Sending functions


async def send_websocket_message_connection(
	user_id: str, connection_id: str, message: WebSocketResponse
) -> None:
	"""Sends a message to a specific WebSocket connection."""
	# Underlying exceptions handled in WebSocketManager
	registry = get_websocket_registry(
		op='send_websocket_message_connection'
	)
	await registry.send_connection(user_id, connection_id, message)


async def send_websocket_message_user(
	user_id: str, message: WebSocketResponse
) -> None:
	"""Sends a message to all WebSocket connections for a user."""
	# Underlying exceptions handled in WebSocketManager
	registry = get_websocket_registry(
		op='send_websocket_message_user'
	)
	await registry.send_user(user_id, message)
