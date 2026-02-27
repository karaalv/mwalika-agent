"""
This module contains schemas for managing
the state of the OpenAI API response stream
in the main agent chat function.
"""

from enum import Enum

from pydantic import BaseModel, Field


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
	block: NdJsonItem | None = Field(
		None,
		description='NDJSON item block if applicable',
	)
