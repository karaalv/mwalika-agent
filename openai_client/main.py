"""
This module acts as the main entry point
for the OpenAI client component of the
Mwalika Agent system.
"""

from typing import Literal, TypeVar

from openai import AsyncStream
from openai.types.responses import (
	ResponseStreamEvent,
	ToolParam,
)
from pydantic import BaseModel

from exceptions.core import ErrorContext
from exceptions.services import OpenAIException
from openai_client.config import (
	OPENAI_RESPONSE_TIMEOUT,
	get_openai_client,
)
from openai_client.limiter import (
	get_openai_embedding_limiter,
	get_openai_response_limiter,
	get_openai_semaphore,
)
from utils.decorators.exceptions import guard

# Generic type for response models
T = TypeVar('T', bound=BaseModel)


# --- Embedding Functionality ---


@guard(
	operation='create_embedding',
	component='openai_client',
	code='embedding_creation_error',
	wrap_cls=OpenAIException,
)
async def create_embedding(
	input: str,
	model: str = 'text-embedding-3-large',
) -> list[float]:
	"""
	Creates an embedding for the given input
	text using the OpenAI API.
	"""
	openai = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_embedding_limiter()
	async with semaphore:
		async with limiter:
			response = await openai.embeddings.create(
				input=input,
				model=model,
				timeout=OPENAI_RESPONSE_TIMEOUT,
			)
			embedding = response.data[0].embedding
			if not embedding:
				raise OpenAIException(
					message='Failed to create embedding.',
					code='embedding_creation_failed',
					context=ErrorContext(
						operation='create_embedding',
						component='openai_client',
						metadata={'input_length': len(input)},
					),
				)
			return embedding


# --- Text Responses ---


@guard(
	operation='normal_response',
	component='openai_client',
	code='response_generation_error',
	wrap_cls=OpenAIException,
)
async def normal_response(
	system_prompt: str,
	user_input: str,
	model: str = 'gpt-5-mini',
	effort: Literal['minimal', 'low', 'medium', 'high'] = 'medium',
	verbosity: Literal['low', 'medium', 'high'] = 'medium',
) -> str:
	"""
	Constructs a normal response from OpenAI.

	Args:
	system_prompt (str): The system prompt to guide
	the model.
	user_input (str): The user's input to the model.
	model (str): The model to use for the response.

	Returns:
	str: The response from the OpenAI client.
	"""
	openai = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_response_limiter()
	async with semaphore:
		async with limiter:
			response = await openai.responses.create(
				model=model,
				instructions=system_prompt,
				input=user_input,
				reasoning={'effort': effort},
				text={'verbosity': verbosity},
				timeout=OPENAI_RESPONSE_TIMEOUT,
			)
			text = response.output_text.strip()

			if not text:
				raise OpenAIException(
					message='Failed to generate response.',
					code='response_generation_failed',
					context=ErrorContext(
						operation='normal_response',
						component='openai_client',
						metadata={
							'model': model,
							'effort': effort,
							'verbosity': verbosity,
						},
					),
				)
			return text


@guard(
	operation='structured_response',
	component='openai_client',
	code='structured_response_error',
	wrap_cls=OpenAIException,
)
async def structured_response(
	system_prompt: str,
	user_prompt: str,
	response_format: type[T],
	model: str = 'gpt-5-mini',
	effort: Literal['low', 'medium', 'high'] = 'low',
) -> T:
	"""
	Constructs a structured response from OpenAI, note
	that validation should be done on the returned object.

	Args:
	system_prompt (str): The system prompt to guide the
	model.
	user_prompt (str): The user's input to the model.
	response_format (Type[T]): The Pydantic model
	to
	structure the response.
	model (str): The model to use for the response.

	Returns:
	T: The structured response from the OpenAI
	client.
	"""
	openai = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_response_limiter()
	async with semaphore:
		async with limiter:
			response = await openai.responses.parse(
				model=model,
				text_format=response_format,
				reasoning={'effort': effort},
				input=[
					{
						'role': 'system',
						'content': system_prompt,
					},
					{
						'role': 'user',
						'content': user_prompt,
					},
				],
				timeout=OPENAI_RESPONSE_TIMEOUT,
			)

			output = response.output_parsed
			if not output:
				raise OpenAIException(
					message=(
						'Failed to generate structured response.'
					),
					code='structured_response_failed',
					context=ErrorContext(
						operation='structured_response',
						component='openai_client',
						metadata={
							'model': model,
							'effort': effort,
							'response_format': (
								response_format.__name__
							),
						},
					),
				)

			if not isinstance(output, response_format):
				raise OpenAIException(
					message=(
						'Response does not match expected format.'
					),
					code='response_format_mismatch',
					context=ErrorContext(
						operation='structured_response',
						component='openai_client',
						metadata={
							'model': model,
							'effort': effort,
							'response_format': (
								response_format.__name__
							),
							'output_type': type(output).__name__,
						},
					),
				)
			return output


async def agent_response_stream(
	system_prompt: str,
	user_input: str,
	tools: list[ToolParam],
	model: str = 'gpt-5-mini',
	effort: Literal['minimal', 'low', 'medium', 'high'] = 'medium',
	verbosity: Literal['low', 'medium', 'high'] = 'medium',
) -> AsyncStream[ResponseStreamEvent]:
	"""
	Returns a stream of responses from OpenAI
	for the agent, including tool calls and outputs.
	"""
	openai = get_openai_client()
	semaphore = get_openai_semaphore()
	limiter = get_openai_response_limiter()
	async with semaphore:
		async with limiter:
			response_stream = await openai.responses.create(
				model=model,
				instructions=system_prompt,
				input=user_input,
				tools=tools,
				reasoning={'effort': effort},
				text={'verbosity': verbosity},
				timeout=OPENAI_RESPONSE_TIMEOUT,
				stream=True,
			)
			return response_stream
