"""
This module defines the triggering mechanism
for the feedback form in the Mwalika Agent system,
including the conditions under which the feedback form
should be presented to users.
"""

from events.lifecycle import publish_websocket_message
from schemas.api.responses import WebSocketMessageType
from schemas.users.core import FeedbackPromptState
from shared.time import get_timestamp_s
from users.service.retrieval import get_anonymous_user
from users.service.update import update_user_feedback_prompt_state

# --- Constants ---

_24_HOURS_S = 24 * 60 * 60

# --- Utility Functions ---


def resolve_time_until_next_prompt(
	prompt_state: FeedbackPromptState, current_time_s: int
) -> int:
	"""
	Calculate the time until the user is next
	eligible for a feedback prompt, based on
	the number of times they've been prompted.
	"""
	request_count = prompt_state.request_count
	if request_count <= 0:
		delta = 0
	elif request_count == 1:
		delta = _24_HOURS_S * 7  # 1 week
	elif request_count == 2:
		delta = _24_HOURS_S * 14  # 2 weeks
	else:
		delta = _24_HOURS_S * 90  # 3 months

	return current_time_s + delta


# --- Main Logic ---


async def trigger_feedback_prompt(
	user_id: str, connection_id: str | None = None
) -> None:
	"""
	Trigger the feedback prompt for a user if
	they are eligible, and update their feedback
	prompt state accordingly.
	"""
	user = await get_anonymous_user(user_id)
	if not user:
		return

	prompt_state = user.feedback_prompt_state or FeedbackPromptState()
	current_time_s = get_timestamp_s()

	# Check if user is eligible for feedback prompt
	if (
		prompt_state.next_eligible_prompt_at_s
		and prompt_state.next_eligible_prompt_at_s > current_time_s
	):
		return

	# Update prompt state to reflect that user has been prompted
	prompt_state.request_count += 1
	prompt_state.last_prompted_at_s = current_time_s
	prompt_state.next_eligible_prompt_at_s = (
		resolve_time_until_next_prompt(prompt_state, current_time_s)
	)
	await update_user_feedback_prompt_state(user_id, prompt_state)

	# Publish websocket message to trigger feedback form on frontend
	message = f'User feedback requested for user {user_id}'
	ws_payload = 'Requesting feedback from user'
	await publish_websocket_message(
		user_id=user_id,
		connection_id=connection_id,
		message_type=WebSocketMessageType.REQUEST_FEEDBACK,
		message=message,
		payload={'message': ws_payload},
		success=True,
	)
