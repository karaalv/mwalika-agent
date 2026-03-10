"""
This module contains schema definitions for the API
requests used in the Mwalika Agent system. These
schemas define the expected structure of data for
various API endpoints, including agent management,
session handling, and other functionalities.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class WebSocketRequestType(str, Enum):
	"""
	Enumeration of possible WebSocket request types
	in the Mwalika Agent system.
	"""

	AGENT_INTERACTION = 'agent_interaction'
	HEARTBEAT = 'heartbeat'


class WebSocketRequestPayload(BaseModel):
	"""
	Represents the payload of a WebSocket request.
	This schema can be extended with specific fields
	depending on the request type.
	"""

	message: str = Field(
		...,
		description=(
			'The message content sent by the client, which can be '
			'used for agent interactions or other purposes'
		),
	)
	session_id: str = Field(
		...,
		description=(
			'The unique identifier for the session associated with '
			'the WebSocket request, used to track interactions '
			'and maintain context'
		),
	)


class WebSocketRequest(BaseModel):
	"""
	Represents a WebSocket request sent by the client
	to the server. This schema defines the structure of
	messages that the server expects to receive over
	WebSocket connections.
	"""

	model_config = ConfigDict(
		extra='forbid',
	)
	type: WebSocketRequestType = Field(
		...,
		description=(
			'The type of the WebSocket request, '
			'which determines how the server '
			'should handle it'
		),
	)
	payload: WebSocketRequestPayload = Field(
		...,
		description=(
			'The actual data payload of the WebSocket '
			'request, which can contain any relevant '
			'information depending on the request type'
		),
	)
