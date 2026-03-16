"""
This module defines core schemas used for the anonymous
user management in the Mwalika Agent system, including
the AnonymousUser schema and related data structures.
"""

from enum import Enum

from pydantic import BaseModel, Field

from shared.time import get_timestamp


class LanguagePreference(str, Enum):
	"""
	Enumeration of possible language preferences
	for users in the Mwalika Agent system.
	"""

	ENGLISH = 'english'
	SWAHILI = 'swahili'


class FeedbackPromptState(BaseModel):
	"""
	Represents the state of feedback prompting
	for an anonymous user, containing timestamps
	for prompt events and eligibility.
	"""

	last_prompted_at_s: int | None = Field(
		default=None,
	)
	last_submitted_at_s: int | None = Field(
		default=None,
	)
	request_count: int = Field(
		default=0,
	)
	next_eligible_prompt_at_s: int | None = Field(
		default=None,
	)


class AnonymousUser(BaseModel):
	"""
	Represents an anonymous user in the
	Mwalika Agent system.
	"""

	user_id: str = Field(
		...,
		description=(
			'A unique identifier for the anonymous user, '
			'which can be used to associate sessions, '
			'memories, and other data with this user'
		),
	)
	language_preference: LanguagePreference = Field(
		default=LanguagePreference.ENGLISH,
		description=(
			'The preferred language of the user, which can be used '
			'to tailor interactions and responses from agents'
		),
	)
	created_at: str = Field(
		default_factory=get_timestamp,
		description=(
			'The timestamp when the anonymous user was created, '
			'which can be useful for tracking user activity and '
			'managing data retention policies'
		),
	)
	last_active_at: str = Field(
		default_factory=get_timestamp,
		description=(
			'The timestamp when the anonymous user was last active, '
			'which can be used to determine if the user is still '
			'active or if their data should be cleaned up after a '
			'certain period'
		),
	)
	feedback_prompt_state: FeedbackPromptState | None = Field(
		default=None,
		description=(
			'The state of feedback prompting for the '
			'user, which can be used to determine when '
			'to trigger feedback forms and manage user '
			'experience around feedback collection'
		),
	)
