"""
This module contains schemas for the agent's memory
component, which is responsible for storing and
retrieving agent interactions and context.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from shared.ids import generate_uuid_str
from shared.time import get_timestamp


class MemoryContentTypes(Enum):
	TEXT = 'text'
	IMAGE = 'image'
	LINK = 'link'


class MemoryContent(BaseModel):
	"""
	Represents the content of a memory entry,
	which can be either text or links to images
	or other resources.
	"""

	type: MemoryContentTypes = Field(
		...,
		description='Type of the memory content (text, image, link)',
	)
	payload: str = Field(
		...,
		description='The actual content value (text or URL)',
	)


class AgentMemory(BaseModel):
	"""
	Represents the memory of an
	agent interaction
	"""

	session_id: str = Field(
		...,
		description='Unique identifier for the agent session',
	)
	user_id: str = Field(
		...,
		description='Unique identifier for the user',
	)
	sender: Literal['user', 'agent'] = Field(
		...,
		description='Indicates who sent the message (user or agent)',
	)
	memory_id: str = Field(
		default_factory=generate_uuid_str,
		description='Unique identifier for the memory entry',
	)
	timestamp: str = Field(
		default_factory=get_timestamp,
		description=(
			'Timestamp of the memory entry in ISO 8601 format'
		),
	)
	content: list[MemoryContent] = Field(
		...,
		description=(
			'List of content items in the memory entry, '
			'which can include text, images, or links'
		),
	)
