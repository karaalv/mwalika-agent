"""
This module contains core schemas for event
management within the Mwalika Agent system, including
definitions for events, subscribers, and the event bus.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from schemas.api.responses import WebSocketResponse
from shared.ids import generate_uuid_str
from shared.time import get_timestamp

EventPayloadUnion = WebSocketResponse | dict[str, Any]


class EventType(str, Enum):
	"""
	Enumeration of possible event types
	in the Mwalika Agent system.
	"""

	WEBSOCKET_MESSAGE = 'websocket_message'


class InMemoryEvent(BaseModel):
	"""
	Represents an event that can be published
	to the InMemoryBus.
	"""

	user_id: str = Field(
		...,
		description=('The ID of the user associated with this event'),
	)
	event_id: str = Field(
		default_factory=generate_uuid_str,
		description='A unique identifier for the event',
	)
	type: EventType = Field(..., description='The type of the event')
	payload: EventPayloadUnion = Field(
		..., description='The data associated with the event'
	)
	event_options: dict[str, Any] = Field(
		default_factory=dict,
		description=(
			'Additional options or metadata for the event, '
			'which can be used by subscribers to handle the event'
		),
	)
	timestamp: str = Field(
		default_factory=get_timestamp,
		description='The timestamp when the event was created',
	)
