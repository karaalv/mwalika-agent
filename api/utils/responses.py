"""
This module contains utilities for defining and
handling API responses.
"""

from typing import Any

from fastapi.responses import JSONResponse

from schemas.api.responses import (
	HttpApiResponse,
	MetaData,
	WebSocketMessage,
	WebSocketMessagePayload,
	WebSocketMessageType,
	WebSocketResponse,
)

# --- HTTP API response utilities ---


def http_response(
	request_id: str,
	success: bool,
	message: str,
	data: Any | None = None,
	status_code: int = 200,
) -> JSONResponse:
	"""
	Utility function to create a standardized
	HTTP API response.
	"""
	response = HttpApiResponse(
		meta=MetaData(
			request_id=request_id,
			success=success,
			message=message,
		),
		data=data,
	)
	return JSONResponse(
		content=response.model_dump(mode='json'),
		status_code=status_code,
	)


# --- WebSocket message utilities ---


def create_websocket_message(
	message_type: WebSocketMessageType,
	payload: WebSocketMessagePayload,
) -> WebSocketMessage:
	"""
	Utility function to create a standardized
	WebSocket message.
	"""
	return WebSocketMessage(type=message_type, payload=payload)


def create_websocket_response(
	request_id: str,
	success: bool,
	message: str,
	message_type: WebSocketMessageType,
	payload: WebSocketMessagePayload,
) -> WebSocketResponse:
	"""
	Utility function to create a JSON string
	representation of a WebSocket message, ready
	to be sent over the WebSocket connection.
	"""
	ws_message = create_websocket_message(
		message_type=message_type, payload=payload
	)
	return WebSocketResponse(
		meta=MetaData(
			request_id=request_id,
			success=success,
			message=message,
		),
		message=ws_message,
	)
