"""
This module defines the submission logic for the
feedback form in the Mwalika Agent system, including
the data structures for feedback submission and the
function to handle feedback form submissions from users.
"""

from enum import Enum
from typing import TypeVar

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.users.core import FeedbackPromptState, LanguagePreference
from schemas.users.feedback import (
	IntendedServiceCategory,
	PromptSource,
	ServiceMatchedQuality,
	UserFeedback,
	WhatHelped,
	WhatWentWrong,
)
from shared.sanitize import scrub_string
from shared.time import get_timestamp_s
from users.feedback.trigger import resolve_time_until_next_prompt
from users.service.retrieval import get_anonymous_user
from users.service.update import update_user_feedback_prompt_state

T = TypeVar('T', bound=Enum)

# --- Helpers ---


def _resolve_enum_value(enum_class: type[T], value: str) -> T | None:
	"""
	Helper function to resolve a string
	value to an enum member.
	"""
	try:
		return enum_class(value)
	except ValueError:
		return None


def _resolve_enum_list(
	enum_class: type[T], values: list[str]
) -> list[T]:
	"""
	Helper function to resolve a list of string
	values to a list of enum members.
	"""
	resolved = []
	for value in values:
		enum_value = _resolve_enum_value(enum_class, value)
		if enum_value:
			resolved.append(enum_value)
	return resolved


# --- Main Logic ---


async def submit_feedback(
	user_id: str,
	request_body: dict,
) -> UserFeedback:
	"""
	Handle the submission of user feedback, including
	validating the input, saving the feedback to the
	database, and updating the user's feedback prompt state.
	"""
	# Validate user exists
	user = await get_anonymous_user(user_id)
	if not user:
		raise ValueError('User not found')

	# Resolve string values from request payload
	session_id = request_body.get('session_id') or ''
	memory_id = request_body.get('memory_id') or ''
	comments = scrub_string(request_body.get('comments') or '')

	# Resolve boolean value for helpful field
	helpful_raw = request_body.get('helpful')
	helpful = None
	if isinstance(helpful_raw, bool):
		helpful = helpful_raw
	elif isinstance(helpful_raw, str):
		helpful_lower = helpful_raw.lower()
		if helpful_lower in ['true', 'yes', '1']:
			helpful = True
		elif helpful_lower in ['false', 'no', '0']:
			helpful = False

	# Resolve enum values from request payload
	language_preference = _resolve_enum_value(
		LanguagePreference,
		request_body.get('language_preference') or '',
	)
	prompt_source = _resolve_enum_value(
		PromptSource, request_body.get('prompt_source') or ''
	)
	intended_service_category = _resolve_enum_value(
		IntendedServiceCategory,
		request_body.get('intended_service_category') or '',
	)
	service_matched_quality = _resolve_enum_value(
		ServiceMatchedQuality,
		request_body.get('service_matched_quality') or '',
	)

	raw_what_helped = request_body.get('what_helped') or []
	if not isinstance(raw_what_helped, list):
		raw_what_helped = []
	what_helped = _resolve_enum_list(WhatHelped, raw_what_helped)

	raw_what_went_wrong = request_body.get('what_went_wrong') or []
	if not isinstance(raw_what_went_wrong, list):
		raw_what_went_wrong = []
	what_went_wrong = _resolve_enum_list(
		WhatWentWrong, raw_what_went_wrong
	)

	# Create feedback object
	feedback = UserFeedback(
		user_id=user_id,
		session_id=session_id,
		memory_id=memory_id,
		language_preference=language_preference,
		prompt_source=prompt_source,
		helpful=helpful,
		intended_service_category=intended_service_category,
		service_matched_quality=service_matched_quality,
		what_helped=what_helped,
		what_went_wrong=what_went_wrong,
		comments=comments,
	)

	# Save feedback to database
	feedback_collection = get_collection(
		MongoDBCollection.USER_FEEDBACK
	)
	await feedback_collection.insert_one(
		feedback.model_dump(mode='json')
	)

	# Update user's feedback prompt state
	current_time_s = get_timestamp_s()
	prompt_state = user.feedback_prompt_state or FeedbackPromptState()
	prompt_state.last_submitted_at_s = current_time_s
	prompt_state.request_count += 1
	prompt_state.next_eligible_prompt_at_s = (
		resolve_time_until_next_prompt(prompt_state, current_time_s)
	)
	await update_user_feedback_prompt_state(
		user_id=user_id, prompt_state=prompt_state
	)

	return feedback
