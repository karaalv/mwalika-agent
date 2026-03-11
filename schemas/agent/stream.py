"""
This module contains schemas for managing
the state of the OpenAI API response stream
in the main agent chat function.
"""

from enum import Enum

from pydantic import BaseModel, Field

from shared.ids import generate_uuid_str
from shared.time import get_timestamp


class StreamState(str, Enum):
	TOOL = 'tool'
	MESSAGE = 'message'


class NdJsonTypes(str, Enum):
	TEXT = 'text'
	IMAGE = 'image'
	LINK = 'link'


class NdJsonItem(BaseModel):
	type: NdJsonTypes = Field(
		...,
		description='Type of the NDJSON item (text, image, or link)',
	)
	payload: str = Field(
		...,
		description='Payload of the NDJSON item',
	)
	title: str = Field(
		...,
		description=(
			'Human-readable title for the NDJSON item, '
			'used for display purposes'
		),
	)


class StreamItem(BaseModel):
	type: NdJsonTypes = Field(
		...,
		description='Type of the NDJSON item (text, image, or link)',
	)
	payload: str = Field(
		...,
		description='Payload of the NDJSON item',
	)
	title: str | None = Field(
		default=None,
		description=(
			'Human-readable title for the NDJSON item, '
			'used for display purposes (optional for text items)'
		),
	)
	user_id: str = Field(
		...,
		description=(
			'Unique identifier for the user '
			'associated with this stream item'
		),
	)
	session_id: str = Field(
		...,
		description=(
			'Unique identifier for the '
			'agent session this item belongs to'
		),
	)
	memory_id: str = Field(
		...,
		description=(
			'Unique identifier for the memory this item belongs to'
		),
	)
	sequence_number: int = Field(
		...,
		description=(
			'Sequence number of this item in the stream, used for '
			'ordering and buffering logic'
		),
	)
	stream_id: str = Field(
		default_factory=generate_uuid_str,
		description=(
			'Unique identifier for this stream item, '
			'useful for tracing and debugging purposes'
		),
	)
	timestamp: str = Field(
		default_factory=get_timestamp,
		description=(
			'The timestamp when this stream item was created, '
			'useful for ordering and debugging purposes'
		),
	)


# --- Stream parsing response schema ---


class StreamParsingCode(str, Enum):
	BLOCK = 'block'
	BUFFER = 'buffer'
	PASSTHROUGH = 'passthrough'
	EMPTY = 'empty'


class StreamParsingResponse(BaseModel):
	code: StreamParsingCode = Field(
		...,
		description=(
			'Code indicating the result of the stream parsing'
		),
	)
	block: StreamItem | None = Field(
		None,
		description='Stream item block if applicable',
	)
