"""
This module contains tests for the InMemoryBus
used in the events component of the Mwalika Agent system.
"""

from events.bus import InMemoryBus
from schemas.events.core import EventType, InMemoryEvent

# --- Test cases ---


async def test_publish_and_get_event():
	bus = InMemoryBus()

	event = InMemoryEvent(
		user_id='test_user',
		event_id='test_event_id',
		type=EventType.WEBSOCKET_MESSAGE,
		payload={'message': 'Hello, World!'},
		event_options={'option1': 'value1'},
	)

	await bus.publish(event)
	received = await bus.get_event()

	assert received == event


async def test_stop_publishes_sentinel():
	bus = InMemoryBus()

	await bus.stop()
	event = await bus.get_event()

	assert event is None
