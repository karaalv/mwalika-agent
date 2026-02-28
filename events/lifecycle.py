"""
This module contains lifecycle utilities for events
related components (singletons, background tasks, etc).
"""

from typing import Any

from api.utils.responses import create_websocket_response
from events.bus import InMemoryBus
from events.forwarder import EventForwarder
from exceptions.core import ErrorContext
from exceptions.events import (
	EventBusException,
)
from schemas.api.responses import (
	WebSocketMessagePayload,
	WebSocketMessageType,
)
from schemas.events.core import (
	EventPayloadUnion,
	EventType,
	InMemoryEvent,
)
from shared.ids import generate_uuid_str
from shared.logging import LogStyle, cprint

# --- Global instances ---

_event_bus: InMemoryBus | None = None
_event_forwarder: EventForwarder | None = None

# --- Lifecycle management ---

# Connection management functions


def start_event_system() -> None:
	"""Initializes the global event bus and forwarder."""
	global _event_bus, _event_forwarder
	if _event_bus is None:
		_event_bus = InMemoryBus()
		_event_bus.start()
		cprint(
			'Event bus initialized.',
			style=LogStyle.SUCCESS,
			prefix='events.lifecycle',
		)
	if _event_forwarder is None:
		_event_forwarder = EventForwarder(bus=_event_bus)
		_event_forwarder.start()
		cprint(
			'Event forwarder started.',
			style=LogStyle.SUCCESS,
			prefix='events.lifecycle',
		)


async def stop_event_system() -> None:
	"""Closes the global event bus and forwarder."""
	global _event_bus, _event_forwarder
	if _event_forwarder is not None:
		await _event_forwarder.stop()
		_event_forwarder = None
		cprint(
			'Event forwarder stopped.',
			style=LogStyle.SUCCESS,
			prefix='events.lifecycle',
		)
	if _event_bus is not None:
		await _event_bus.stop()
		_event_bus = None
		cprint(
			'Event bus stopped.',
			style=LogStyle.SUCCESS,
			prefix='events.lifecycle',
		)


# Setter functions
def set_event_bus(bus: InMemoryBus | None) -> None:
	"""Sets the global event bus instance (for testing)."""
	global _event_bus
	_event_bus = bus


def set_event_forwarder(forwarder: EventForwarder | None) -> None:
	"""Sets the global event forwarder instance (for testing)."""
	global _event_forwarder
	_event_forwarder = forwarder


# --- Event bus functions ---


async def publish_event(
	user_id: str,
	event_type: EventType,
	payload: EventPayloadUnion,
	event_options: dict[str, Any] | None = None,
) -> None:
	"""Publishes an event to the global event bus."""
	if _event_bus is None:
		raise EventBusException(
			message='Event bus is not initialized.',
			code='event_bus_none',
			context=ErrorContext(
				operation='publish_event',
				component='events.lifecycle',
				metadata={
					'user_id': user_id,
					'event_type': event_type,
					'event_options': event_options,
				},
			),
		)
	event = InMemoryEvent(
		user_id=user_id,
		type=event_type,
		payload=payload,
		event_options=event_options or {},
	)
	await _event_bus.publish(event)


async def publish_websocket_message(
	user_id: str,
	message_type: WebSocketMessageType,
	payload: WebSocketMessagePayload,
	message: str,
	connection_id: str | None = None,
	success: bool = True,
	event_options: dict[str, Any] | None = None,
) -> None:
	"""
	Utility function to publish a WebSocket
	message event.
	"""
	ws_response = create_websocket_response(
		request_id=generate_uuid_str(),
		success=success,
		message=message,
		message_type=message_type,
		payload=payload,
	)

	# Add connection_id to event options if provided
	event_options = event_options or {}
	if connection_id:
		event_options['connection_id'] = connection_id

	await publish_event(
		user_id=user_id,
		event_type=EventType.WEBSOCKET_MESSAGE,
		payload=ws_response,
		event_options=event_options,
	)
