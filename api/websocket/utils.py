"""
This module contains helper functions and utilities
for managing WebSocket connections in the Mwalika
Agent system, including packaging messages and common
processing tasks related to WebSocket communication.
"""

from schemas.api.responses import (
	MetaData,
	WebSocketMessage,
	WebSocketMessagePayload,
	WebSocketMessageType,
	WebSocketResponse,
)


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
