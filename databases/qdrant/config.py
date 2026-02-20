"""
This module contains configuration settings
for the Qdrant client. It handles
connection setup and client initialization.
"""

from os import getenv

from qdrant_client import AsyncQdrantClient

from exceptions.core import ErrorContext
from exceptions.databases import QdrantException
from shared.logging import LogStyle, cprint

# --- Configuration ---

QDRANT_TIMEOUT_S = 30

# Global Qdrant Client
_qdrant_client: AsyncQdrantClient | None = None

# --- Client Management ---

# Connection management functions


def start_qdrant_client() -> None:
	"""Initializes the global Qdrant client."""
	global _qdrant_client
	if _qdrant_client is None:
		qdrant_url = getenv('QDRANT_URL')
		qdrant_api_key = getenv('QDRANT_API_KEY')
		if not qdrant_url or not qdrant_api_key:
			raise QdrantException(
				message=(
					'QDRANT_URL and QDRANT_API_KEY '
					'environment variables must be set.'
				),
				code='qdrant_config_incomplete',
				context=ErrorContext(
					operation='start_qdrant_client',
					component='qdrant.config',
				),
			)

		try:
			cprint(
				'Initializing Qdrant client...',
				style=LogStyle.INFO,
				prefix='qdrant.config',
			)
			_qdrant_client = AsyncQdrantClient(
				url=qdrant_url,
				api_key=qdrant_api_key,
				timeout=QDRANT_TIMEOUT_S,
			)
			cprint(
				'Qdrant client initialized.',
				style=LogStyle.SUCCESS,
				prefix='qdrant.config',
			)
		except Exception as e:
			raise QdrantException(
				message=(
					f'Failed to initialize Qdrant client: {str(e)}'
				),
				code='qdrant_client_init_failed',
				context=ErrorContext(
					operation='start_qdrant_client',
					component='qdrant.config',
				),
				cause=e,
			) from e


async def close_qdrant_client() -> None:
	"""Closes the global Qdrant client."""
	global _qdrant_client
	if _qdrant_client is not None:
		try:
			cprint(
				'Closing Qdrant client...',
				style=LogStyle.INFO,
				prefix='qdrant.config',
			)
			await _qdrant_client.close()
			set_qdrant_client(None)
			cprint(
				'Qdrant client closed.',
				style=LogStyle.SUCCESS,
				prefix='qdrant.config',
			)
		except Exception as e:
			raise QdrantException(
				message=(f'Failed to close Qdrant client: {str(e)}'),
				code='qdrant_client_close_failed',
				context=ErrorContext(
					operation='close_qdrant_client',
					component='qdrant.config',
				),
				cause=e,
			) from e


# Client accessors


def get_qdrant_client() -> AsyncQdrantClient:
	"""Returns the global Qdrant client."""
	global _qdrant_client
	if _qdrant_client is None:
		raise QdrantException(
			message='Qdrant client is not initialized.',
			code='qdrant_client_none',
			context=ErrorContext(
				operation='get_qdrant_client',
				component='qdrant.config',
			),
		)

	return _qdrant_client


def set_qdrant_client(
	client: AsyncQdrantClient | None,
) -> None:
	"""Sets the global Qdrant client."""
	global _qdrant_client
	_qdrant_client = client


# Session management functions


async def is_qdrant_connected() -> bool:
	"""Checks if the Qdrant client is connected."""
	client = get_qdrant_client()
	try:
		await client.get_collections()
		return True
	except Exception:
		return False
