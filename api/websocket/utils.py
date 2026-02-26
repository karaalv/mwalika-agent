"""
This module contains helper functions and utilities
for managing WebSocket connections in the Mwalika
Agent system, including packaging messages and common
processing tasks related to WebSocket communication.
"""

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from events.lifecycle import publish_event
from schemas.api.responses import (
	MetaData,
	WebSocketMessage,
	WebSocketMessagePayload,
	WebSocketMessageType,
	WebSocketResponse,
)
from schemas.events.core import EventType
from shared.ids import generate_uuid_str


def create_websocket_response(
	message_type: WebSocketMessageType,
	payload: WebSocketMessagePayload,
	request_id: str,
	success: bool = True,
	message: str = '',
) -> WebSocketResponse:
	"""
	Creates a WebSocketResponse object with the given
	parameters, including metadata.
	"""
	return WebSocketResponse(
		meta=MetaData(
			request_id=request_id, success=success, message=message
		),
		message=WebSocketMessage(type=message_type, payload=payload),
	)


async def send_websocket_error_directly(
	websocket: WebSocket,
	error_message: str,
	request_id: str,
	connection_id: str,
) -> None:
	"""
	Sends an error message directly to the client over the WebSocket
	connection without using the event bus, which can be useful for
	immediately notifying the client of issues such as authentication
	failures or invalid messages.
	"""
	error_response = create_websocket_response(
		message_type=WebSocketMessageType.ERROR,
		payload={
			'error': error_message,
			'connection_id': connection_id,
		},
		request_id=request_id,
		success=False,
		message=error_message,
	)
	await websocket.send_json(error_response.model_dump(mode='json'))


async def ws_send_error_and_close(
	websocket: WebSocket,
	error_message: str,
	request_id: str,
	connection_id: str,
) -> None:
	"""
	Utility function to send an error message through the websocket
	and then close the connection.
	"""
	if websocket.client_state != WebSocketState.CONNECTED:
		await websocket.accept()
	await send_websocket_error_directly(
		websocket=websocket,
		error_message=error_message,
		request_id=request_id,
		connection_id=connection_id,
	)
	if websocket.client_state == WebSocketState.CONNECTED:
		await websocket.close(code=1008)


async def publish_websocket_message_event(
	user_id: str,
	connection_id: str,
	message: WebSocketMessagePayload,
	message_type: WebSocketMessageType,
) -> None:
	"""
	Utility function to send a WebSocket message to the client
	by publishing an event to the event bus.
	"""
	ws_response = create_websocket_response(
		request_id=generate_uuid_str(),
		success=True,
		message='',
		message_type=message_type,
		payload=message,
	)
	await publish_event(
		user_id=user_id,
		event_type=EventType.WEBSOCKET_MESSAGE,
		payload=ws_response,
		event_options={'connection_id': connection_id},
	)
