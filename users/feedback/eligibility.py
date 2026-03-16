"""
This module defines the eligibility criteria for
the application to trigger the feedback form for
users in the Mwalika Agent system.
"""

from schemas.users.core import FeedbackPromptState
from shared.logging import LogStyle, cprint
from shared.time import get_timestamp_s
from users.service.retrieval import get_anonymous_user
from users.service.update import update_user_feedback_prompt_state

# --- Constants ---


# --- Main Logic ---


async def mark_user_for_feedback_prompt(
	user_id: str, verbosity_level: int = 0
) -> None:
	"""
	Update the user's feedback prompt state to indicate
	they are eligible to be prompted for feedback, if
	they are not already eligible.
	"""
	user = await get_anonymous_user(user_id)
	if not user:
		return

	prompt_state = user.feedback_prompt_state or FeedbackPromptState()
	current_time_s = get_timestamp_s()

	# If user is already eligible for prompt, do nothing
	if (
		prompt_state.next_eligible_prompt_at_s
		and prompt_state.next_eligible_prompt_at_s > current_time_s
	):
		return

	# Update prompt state to make user eligible for feedback prompt
	prompt_state.next_eligible_prompt_at_s = current_time_s
	await update_user_feedback_prompt_state(user_id, prompt_state)

	if verbosity_level > 0:
		cprint(
			f'Marked user {user_id} eligible for feedback prompt',
			style=LogStyle.INFO,
		)
