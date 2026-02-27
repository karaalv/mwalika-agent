"""
This module contains schema definitions for the API
responses used in the Mwalika Agent system. These
schemas are for regular API responses and WebSocket
streaming responses.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from schemas.agent.stream import NdJsonItem
from shared.time import get_timestamp

# --- Metadata schema for API responses ---


class MetaData(BaseModel):
	request_id: str = Field(
		...,
		description=(
			'A unique identifier for this API response, useful for '
			'tracing and debugging purposes'
		),
	)
	success: bool = Field(
		...,
		description=('Indicates whether the API call was successful'),
	)
	message: str = Field(
		...,
		description=(
			'A human-readable message providing '
			'additional information about the API response'
		),
	)
	timestamp: str = Field(
		default_factory=get_timestamp,
		description=(
			'The timestamp when the API response was generated'
		),
	)


# --- HTTP API response schema ---


class APIResponse(BaseModel):
	meta: MetaData = Field(
		..., description='Metadata about the API response'
	)
	data: Any | None = Field(
		default=None,
		description=(
			'The actual data payload of the API response, '
			'which can be of any type depending on the endpoint'
		),
	)


# --- WebSocket response schema ---

WebSocketMessagePayload = NdJsonItem | str | dict[str, Any]


class WebSocketMessageType(str, Enum):
	HEARTBEAT = 'heartbeat'
	AGENT_RESPONSE = 'agent_response'
	TOOL_MESSAGE = 'tool_message'
	SET_USER_ID = 'set_user_id'
	SET_SESSION_ID = 'set_session_id'
	WARNING = 'warning'
	ERROR = 'error'


class WebSocketMessage(BaseModel):
	type: WebSocketMessageType = Field(
		...,
		description=('The type of the WebSocket message.'),
	)
	payload: WebSocketMessagePayload = Field(
		...,
		description=(
			'The actual content of the WebSocket message, which '
			'can be of any type depending on the message type'
		),
	)


class WebSocketResponse(BaseModel):
	meta: MetaData = Field(
		..., description='Metadata about the WebSocket response'
	)
	message: WebSocketMessage = Field(
		...,
		description=(
			'The WebSocket message containing the type and payload '
			'to be sent to the client'
		),
	)
