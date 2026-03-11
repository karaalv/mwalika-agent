"""
This module defines the prompt templates for agent
behaviour, specifically related to language and other
adjacent properties that the agent should adhere to when
generating responses. This is DIFFERENT FROM THE MAIN
SYSTEM PROMPT, which defines the agent's core identity,
values, and high-level instructions.
"""

from textwrap import dedent

from schemas.users.core import LanguagePreference
from users.service.retrieval import get_anonymous_user

# --- Prompt templates ---

_SWAHILI_BEHAVIOUR_PROMPT = dedent("""
	[AGENT BEHAVIOUR INSTRUCTIONS]

	The user's preferred language is Swahili.

	Begin and continue the conversation primarily in Swahili.

	If the user writes in Swahili, respond in clear, natural
	Swahili.

	If the user uses Sheng, slang, or mixes Swahili and
	English, follow their lead on a best-effort basis while
	keeping the response clear, natural, and easy to
	understand.

	Do not force overly formal or rigid Swahili if the user is
	communicating more casually.

	If the user switches fully into English, you may switch to
	English and continue naturally.

	If the user mixes languages, respond in the style that
	best matches their latest message.

	Maintain the same helpful, neutral, and supportive tone at
	all times.
""").strip()

_ENGLISH_BEHAVIOUR_PROMPT = dedent("""
	[AGENT BEHAVIOUR INSTRUCTIONS]

	The user's preferred language is English.

	Begin and continue the conversation in clear,
	straightforward English.

	If the user switches to Swahili, Sheng, slang, or mixed
	language, follow their lead naturally and respond in the
	language style that best matches their latest message.

	Otherwise, default to normal English.

	Maintain the same helpful, neutral, and supportive tone at
	all times.
""").strip()


async def get_agent_behaviour_prompt(user_id: str) -> str:
	"""
	Return user-specific behaviour instructions for the agent.

	These instructions currently guide language choice based
	on the user's saved language preference.
	"""
	user = await get_anonymous_user(user_id)

	if not user:
		return _ENGLISH_BEHAVIOUR_PROMPT

	if user.language_preference == LanguagePreference.SWAHILI:
		return _SWAHILI_BEHAVIOUR_PROMPT

	return _ENGLISH_BEHAVIOUR_PROMPT
