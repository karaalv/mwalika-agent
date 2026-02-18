"""
This module is used to manage collection
access for QdrantDB operations in the Mwalika
Agent system.
"""

from typing import Final

from qdrant_client.models import Distance, VectorParams

from databases.qdrant.config import get_qdrant_client
from exceptions.core import ErrorContext
from exceptions.databases import QdrantException

# --- Constants ---

COLLECTION_NAME: Final[str] = 'mwalika_corpus'
VECTOR_SIZE: Final[int] = 3072

# --- Collection Management ---


async def ensure_collection_exists(
	collection_name: str = COLLECTION_NAME,
) -> None:
	"""
	Ensures that a Qdrant collection with the specified
	name exists, creating it if necessary.
	"""
	client = get_qdrant_client()
	exists = await collection_exists(collection_name)
	if not exists:
		try:
			result = await client.create_collection(
				collection_name=collection_name,
				vectors_config=VectorParams(
					size=VECTOR_SIZE,
					distance=Distance.COSINE,
				),
			)
			if not result:
				raise QdrantException(
					message=(
						f'Failed to create collection '
						f'"{collection_name}".'
					),
					code='collection_creation_failed',
					context=ErrorContext(
						operation='ensure_collection_exists',
						component='qdrant.collection',
						metadata={
							'collection_name': (
								collection_name
							)
						},
					),
				)
		except Exception as e:
			raise QdrantException(
				message=(
					f'Failed to create collection '
					f'"{collection_name}".'
				),
				code='collection_creation_failed',
				context=ErrorContext(
					operation='ensure_collection_exists',
					component='qdrant.collection',
					metadata={
						'collection_name': collection_name
					},
				),
				cause=e,
			) from e


# --- Collection inspection ---


async def collection_exists(
	collection_name: str = COLLECTION_NAME,
) -> bool:
	"""
	Checks if a Qdrant collection with the specified
	name exists.
	"""
	client = get_qdrant_client()
	try:
		exists = await client.get_collection(
			collection_name
		)
		return exists is not None
	except Exception as e:
		if 'not found' in str(e).lower():
			return False
		raise QdrantException(
			message=(
				f'Failed to check existence of collection '
				f'"{collection_name}".'
			),
			code='collection_existence_check_failed',
			context=ErrorContext(
				operation='collection_exists',
				component='qdrant.collection',
				metadata={
					'collection_name': collection_name
				},
			),
			cause=e,
		) from e
