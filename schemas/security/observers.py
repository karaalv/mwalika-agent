"""
This module contains schemas for resources related to security
observers in the Mwalika Agent system, such as user usage statistics
and other relevant data structures that can be used for monitoring,
analytics, and enforcing security policies.
"""

from enum import Enum

from pydantic import BaseModel, Field

from shared.time import get_timestamp


class BlockedEntityType(str, Enum):
	"""
	Enumeration of possible types of entities that can be blocked
	in the Mwalika Agent system, such as users, IP addresses, or
	other relevant identifiers.
	"""

	USER = 'user'
	IP = 'ip'
	REFRESH_TOKEN = 'refresh_token'
	ACCESS_TOKEN = 'access_token'


class BlockedEntity(BaseModel):
	"""
	Represents an entity that has been blocked in the Mwalika Agent
	system, which can be used to track and manage blocked users, IP
	addresses, or other identifiers.
	"""

	entity_type: BlockedEntityType = Field(
		...,
		description=(
			'The type of the blocked entity, which can be a user, '
			'IP address, token, or other relevant identifier that '
			'is subject to blocking based on security policies and '
			'observed behavior'
		),
	)
	entity_id: str = Field(
		...,
		description=(
			'The unique identifier of the blocked entity, such as '
			'a user ID, IP address, or other relevant identifier '
			'that can be used to enforce blocks and manage security '
			'policies'
		),
	)
	blocked_at: str = Field(
		default_factory=get_timestamp,
		description=(
			'The timestamp when the entity was blocked, which can be '
			'useful for tracking block durations and managing data '
			'retention policies'
		),
	)
	blocked_until: int = Field(
		...,
		description=(
			'An optional timestamp indicating when the block will be '
			'lifted, which can be used for temporary blocks or '
			'suspensions based on behavior or policy violations'
		),
	)
	reason: str = Field(
		...,
		description=(
			'The reason for blocking the entity, which can be used '
			'for auditing, and providing feedback to users '
			'or administrators about security actions taken'
		),
	)


class MinuteCounter(BaseModel):
	"""
	Represents a counter for tracking the number of events that
	occur within a specific minute, which can be used for enforcing
	per-minute rate limits in the Mwalika Agent system.
	"""

	minute_key: int = Field(
		...,
		description=(
			'An integer representing the specific minute '
			'(e.g., 202406011234) used to track events that '
			'occur within that minute for rate limiting purposes'
		),
	)
	count: int = Field(
		default=0,
		description=(
			'The count of events that have occurred within the '
			'specified minute, which can be incremented and checked '
			'against defined rate limits to enforce security policies'
		),
	)


class DbWriteBackTaskType(str, Enum):
	"""
	Enumeration of possible tasks for writing back data to the
	database during observer operations, this is done for
	persisting in-memory state outside of the observer lock.
	"""

	PUSH_BLOCKED_ENTITY = 'push_blocked_entity'
	DELETE_BLOCKED_ENTITY = 'delete_blocked_entity'


class DbWriteBackTask(BaseModel):
	"""
	Represents a task for writing back data to the database during
	observer operations, which can be used to persist in-memory state
	changes related to blocks or other security-related actions.
	"""

	task_type: DbWriteBackTaskType = Field(
		..., description=('The type of the database write-back task,')
	)
	blocked_entity: BlockedEntity | None = Field(
		...,
		description=(
			'The blocked entity associated with this '
			'database write-back '
		),
	)
