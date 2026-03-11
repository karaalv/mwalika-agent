"""
This module contains internationalisation logic
for swahili language support in the Mwalika Agent system,
such as translation utilities, language-specific prompt templates,
and any other language-specific processing related to swahili.
"""

from textwrap import dedent

from openai_client.main import normal_response

# --- Prompts ---

_TRANSLATION_PROMPT = dedent("""
    Translate the following text into clear, common Swahili.

    Use simple and natural language that an everyday
    Kenyan speaker would easily understand.

    Do not explain the translation.
    Return only the translated text.
""").strip()


async def translate_to_swahili(text: str) -> str:
	"""
	Translates the given text into clear, natural Swahili
	using the OpenAI API.

	This function is used to ensure that any agent-generated
	content that needs to be in Swahili is properly translated
	while maintaining a natural and easy-to-understand style.
	"""
	translation = await normal_response(
		system_prompt=_TRANSLATION_PROMPT,
		user_input=text,
		model='gpt-5-nano',
		effort='low',
		verbosity='low',
	)
	return translation.strip()
