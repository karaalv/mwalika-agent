"""
This module contains the configuration settings
for the OpenAI client. It handles the main client
configuration used across the application.
"""

from os import getenv

from openai import AsyncOpenAI

from exceptions.core import ErrorContext
from exceptions.services import OpenAIException
from shared.logging import LogStyle, cprint

# --- Configuration ---
OPENAI_RESPONSE_TIMEOUT = 90

# Global OpenAI Client
_openai_client: AsyncOpenAI | None = None

# --- Client Management ---

# Connection management functions


def start_openai_client() -> None:
	"""Initializes the global OpenAI client."""
	global _openai_client
	if _openai_client is None:
		_openai_client = AsyncOpenAI(
			api_key=getenv('OPENAI_API_KEY')
		)
		cprint(
			'OpenAI client initialized.',
			style=LogStyle.SUCCESS,
			prefix='openai.config',
		)


async def close_openai_client() -> None:
	"""Closes the global OpenAI client."""
	openai = get_openai_client()
	if openai is not None:
		await openai.close()
		set_openai_client(None)
		cprint(
			'OpenAI client closed.',
			style=LogStyle.SUCCESS,
			prefix='openai.config',
		)


# Client accessors


def get_openai_client() -> AsyncOpenAI:
	"""Returns the global OpenAI client."""
	global _openai_client
	if _openai_client is None:
		raise OpenAIException(
			message='OpenAI client is not initialized.',
			code='openai_client_none',
			context=ErrorContext(
				operation='get_openai_client',
				component='openai.config',
			),
		)

	return _openai_client


def set_openai_client(client: AsyncOpenAI | None) -> None:
	"""Sets the global OpenAI client."""
	global _openai_client
	_openai_client = client


# Session management functions


async def is_openai_connected() -> bool:
	"""Checks if the OpenAI client is connected."""
	client = get_openai_client()
	try:
		# Perform a simple API call to check connectivity
		await client.models.list()
		return True
	except Exception:
		return False
