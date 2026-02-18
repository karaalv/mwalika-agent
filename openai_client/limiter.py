"""
This module defines the rate limiter for
the OpenAI client. It ensures that requests
to the OpenAI API are made within the allowed
rate limits to prevent throttling or blocking.
"""

from asyncio import Semaphore
from functools import lru_cache
from os import getenv
from typing import Final

from aiolimiter import AsyncLimiter

# --- Configuration ---

_MAX_CONCURRENT_REQUESTS: Final[int] = int(
	getenv('OPENAI_MAX_CONCURRENT_REQUESTS', '8')
)
_RPM_RESPONSES: Final[int] = int(
	getenv('OPENAI_RPM_RESPONSES', '400')
)
_RPM_EMBEDDINGS: Final[int] = int(
	getenv('OPENAI_RPM_EMBEDDINGS', '2000')
)

# --- Rate Limiter Implementation ---


@lru_cache(maxsize=1)
def get_openai_semaphore() -> Semaphore:
	"""
	Returns a semaphore to limit the number of concurrent
	requests to the OpenAI API.
	"""
	return Semaphore(_MAX_CONCURRENT_REQUESTS)


@lru_cache(maxsize=1)
def get_openai_response_limiter() -> AsyncLimiter:
	"""
	Returns an AsyncLimiter to limit the rate of requests
	to the OpenAI API.
	"""
	return AsyncLimiter(_RPM_RESPONSES, 60)


@lru_cache(maxsize=1)
def get_openai_embedding_limiter() -> AsyncLimiter:
	"""
	Returns an AsyncLimiter to limit the rate of embedding
	requests to the OpenAI API.
	"""
	return AsyncLimiter(_RPM_EMBEDDINGS, 60)
