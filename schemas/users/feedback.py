"""
This module defines schemas for the feedback system
for users on the application.
"""

from enum import Enum

from pydantic import BaseModel, Field

from schemas.users.core import LanguagePreference
from shared.ids import generate_uuid_str
from shared.time import get_timestamp

# --- Enum definitions for fields ---


class PromptSource(str, Enum):
	"""
	Possible sources for feedback prompts
	in the Mwalika Agent system.
	"""

	AGENT = 'agent'
	USER_TRIGGERED = 'user_triggered'


class IntendedServiceCategory(str, Enum):
	"""
	Possible intended service categories for feedback
	in the Mwalika Agent system.
	"""

	KRA = 'kra'
	NTSA = 'ntsa'
	BRS = 'brs'
	OTHER = 'other'


class ServiceMatchedQuality(str, Enum):
	"""
	Possible values for service match
	quality in feedback in the Mwalika
	Agent system.
	"""

	YES = 'yes'
	PARTLY = 'partly'
	NO = 'no'


class WhatHelped(str, Enum):
	"""
	Possible values for what helped in feedback
	in the Mwalika Agent system.
	"""

	FOUND_SERVICE = 'found_service'
	SAVED_TIME = 'saved_time'
	CLARITY = 'clarity'
	EASE_OF_USE = 'ease_of_use'


class WhatWentWrong(str, Enum):
	"""
	Possible values for what went wrong in feedback
	in the Mwalika Agent system.
	"""

	DID_NOT_FIND_SERVICE = 'did_not_find_service'
	UNCLEAR_ANSWER = 'unclear_answer'
	TOO_SLOW = 'too_slow'
	DID_NOT_UNDERSTAND = 'did_not_understand'
	WRONG_INFORMATION = 'wrong_information'
	OTHER = 'other'


class FeedbackStatus(str, Enum):
	"""
	Possible statuses for feedback submissions
	in the Mwalika Agent system.
	"""

	NEW = 'new'
	REVIEWED = 'reviewed'
	ACTIONED = 'actioned'
	DISMISSED = 'dismissed'


# --- Main schema ---


class UserFeedback(BaseModel):
	"""
	Represents a user feedback submission in the
	Mwalika Agent system, containing details about
	the feedback and its context.
	"""

	feedback_id: str = Field(
		default_factory=generate_uuid_str,
		description=(
			'A unique identifier for the feedback submission.'
		),
	)
	user_id: str = Field(
		...,
		description=(
			'The identifier of the user who submitted the feedback.'
		),
	)
	session_id: str = Field(
		...,
		description=(
			'The identifier of the session during '
			'which the feedback was submitted.'
		),
	)
	memory_id: str = Field(
		...,
		description=(
			'The identifier of the memory associated with the '
			'feedback submission.'
		),
	)
	language_preference: LanguagePreference | None = Field(
		default=None,
		description=(
			'The language preference of the user at the time of '
			'feedback submission.'
		),
	)
	prompt_source: PromptSource | None = Field(
		default=None,
		description=(
			'The source that triggered the feedback prompt.'
		),
	)
	helpful: bool | None = Field(
		default=None,
		description=(
			'Indicates whether the user found the service helpful.'
		),
	)
	intended_service_category: IntendedServiceCategory | None = Field(
		default=None,
		description=(
			'The category of service the user intended to access.'
		),
	)
	service_matched_quality: ServiceMatchedQuality | None = Field(
		default=None,
		description=(
			"The user's assessment of how well"
			'the service matched their needs.'
		),
	)
	what_helped: list[WhatHelped] = Field(
		default_factory=list,
		description=(
			'A list of factors that helped'
			'the user in their interaction.'
		),
	)
	what_went_wrong: list[WhatWentWrong] = Field(
		default_factory=list,
		description=('A list of issues that users encountered.'),
	)
	comments: str | None = Field(
		default=None,
		description=('Any additional comments provided by the user.'),
	)
	status: FeedbackStatus = Field(
		default=FeedbackStatus.NEW,
		description=(
			'The current status of the feedback submission.'
		),
	)
	submitted_at: str = Field(
		default_factory=get_timestamp,
		description=(
			'The timestamp when the feedback was submitted.'
		),
	)
