"""
This module contains tests for the EventForwarder component
used in the Mwalika Agent system to forward events from the
InMemoryBus to the appropriate subscribers (e.g., WebSocket
connections).
"""

import asyncio

from pytest import MonkeyPatch

from events.bus import InMemoryBus
from events.forwarder import EventForwarder
from schemas.api.responses import (
	MetaData,
	WebSocketMessage,
	WebSocketMessageType,
	WebSocketResponse,
)
from schemas.events.core import EventType, InMemoryEvent

# --- Utils ---


def _create_test_ws_response(message: str) -> WebSocketResponse:
	return WebSocketResponse(
		meta=MetaData(
			request_id='test-request-id',
			success=True,
			message='Test WebSocket response',
		),
		message=WebSocketMessage(
			type=WebSocketMessageType.HEARTBEAT,
			payload=message,
		),
	)


def _create_test_ws_event(
	message: str, connection_id: str | None = None
) -> InMemoryEvent:
	event_options = {}
	if connection_id:
		event_options['connection_id'] = connection_id

	return InMemoryEvent(
		user_id='test-user-id',
		type=EventType.WEBSOCKET_MESSAGE,
		payload=_create_test_ws_response(message),
		event_options=event_options,
	)


# --- Tests ---


async def test_event_forwarder_forward_ws_event(
	monkeypatch: MonkeyPatch,
):
	# Create an InMemoryBus and EventForwarder
	bus = InMemoryBus()
	bus.start()

	forwarder = EventForwarder(bus=bus)
	forwarder.start()

	# --- Test forwarding to user ---

	# Mock the WebSocket sending functions to
	# capture calls
	sent_messages_user: list[tuple[str, WebSocketResponse]] = []

	async def mock_send_websocket_message_user(
		user_id: str, message: WebSocketResponse
	):
		sent_messages_user.append((user_id, message))

	monkeypatch.setattr(
		'events.forwarder.send_websocket_message_user',
		mock_send_websocket_message_user,
	)

	# Create a test event and publish it to the bus
	test_message = 'Hello, WebSocket!'
	test_event = _create_test_ws_event(test_message)
	await bus.publish(test_event)

	# Allow some time for the forwarder to process the event
	await asyncio.sleep(0.1)

	# Assert that the message was forwarded correctly
	assert len(sent_messages_user) == 1
	user_id, message = sent_messages_user[0]
	assert user_id == 'test-user-id'
	assert isinstance(message, WebSocketResponse)
	assert message.message.payload == test_message

	# --- Test forwarding to specific connection ---

	sent_messages_connection: list[
		tuple[str, str, WebSocketResponse]
	] = []

	async def mock_send_websocket_message_connection(
		user_id: str, connection_id: str, message: WebSocketResponse
	):
		sent_messages_connection.append(
			(user_id, connection_id, message)
		)

	monkeypatch.setattr(
		'events.forwarder.send_websocket_message_connection',
		mock_send_websocket_message_connection,
	)

	# Create a test event with a specific connection_id and publish it
	test_connection_id = 'test-connection-id'
	test_event_with_connection = _create_test_ws_event(
		message=test_message,
		connection_id=test_connection_id,
	)
	await bus.publish(test_event_with_connection)

	# Allow some time for the forwarder to process the event
	await asyncio.sleep(0.1)

	# Assert that the message was forwarded to the specific connection
	assert len(sent_messages_connection) == 1
	user_id, connection_id, message = sent_messages_connection[0]
	assert user_id == 'test-user-id'
	assert connection_id == test_connection_id
	assert isinstance(message, WebSocketResponse)
	assert message.message.payload == test_message

	# Stop the forwarder
	await forwarder.stop()
	await bus.stop()
