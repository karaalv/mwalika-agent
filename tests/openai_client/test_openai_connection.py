"""OpenAI client connection test"""

from openai_client.config import (
	is_openai_connected,
)


async def test_openai_connection():
	"""
	Test connection to OpenAI API
	for the AI Engine.
	"""
	assert await is_openai_connected() is True
