"""
This module tests the OpenAI client functions.
"""

from pydantic import BaseModel, Field

from openai_client.main import (
	create_embedding,
	normal_response,
	structured_response,
)


async def test_create_embedding():
	"""
	Tests the OpenAI embedding functionality.
	"""
	embedding = await create_embedding('Hello, world!')
	assert isinstance(embedding, list)
	assert len(embedding) > 0


async def test_normal_response():
	"""
	Tests the OpenAI normal response functionality.
	"""
	response = await normal_response(
		system_prompt='You are a helpful assistant.',
		user_input='What is the capital of France?',
	)
	assert isinstance(response, str)
	assert 'Paris' in response


async def test_structured_response():
	"""
	Tests the OpenAI structured response functionality.
	"""

	class TestOpenAIClient(BaseModel):
		response: str = Field(
			..., description='Response to the user query.'
		)

	response = await structured_response(
		system_prompt='You are a helpful assistant.',
		user_prompt=(
			'Can you provide a summary of the latest news?'
		),
		response_format=TestOpenAIClient,
	)
	assert isinstance(response, TestOpenAIClient)
