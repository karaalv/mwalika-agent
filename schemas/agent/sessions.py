"""
This module contains schemas for managing
sessions of agent interactions, including session
metadata and state.
"""

from pydantic import BaseModel, Field

from shared.time import get_timestamp


class AgentSession(BaseModel):
	"""
	Represents a session of interaction with the agent,
	including metadata such as session ID, user ID, and
	timestamps.
	"""

	session_id: str = Field(
		...,
		description='Unique identifier for the agent session',
	)
	user_id: str = Field(
		...,
		description='Unique identifier for the user',
	)
	chat_name: str = Field(
		...,
		description='Name of the chat session for display purposes',
	)
	created_at: str = Field(
		default_factory=get_timestamp,
		description='Timestamp when the session was created',
	)
	last_active_at: str = Field(
		default_factory=get_timestamp,
		description='Timestamp when the session was last active',
	)
