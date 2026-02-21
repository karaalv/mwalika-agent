"""
This module contains lifecycle utilities for events
related components (singletons, background tasks, etc).
"""

from typing import Any

from events.bus import InMemoryBus
from events.forwarder import EventForwarder
from exceptions.core import ErrorContext
from exceptions.events import (
	EventBusException,
)
from schemas.events.core import (
	EventPayloadUnion,
	EventType,
	InMemoryEvent,
)
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
		_event_forwarder = EventForwarder()
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


async def get_next_event() -> InMemoryEvent | None:
	"""Retrieves the next event from the global event bus."""
	if _event_bus is None:
		raise EventBusException(
			message='Event bus is not initialized.',
			code='event_bus_none',
			context=ErrorContext(
				operation='get_next_event',
				component='events.lifecycle',
			),
		)
	return await _event_bus.get_event()
