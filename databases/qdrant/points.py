"""
This module contains functionality related to
points in QdrantDB, including point creation,
and deletion.
"""

from typing import cast

from qdrant_client.http.models import ExtendedPointId
from qdrant_client.models import PointIdsList, PointStruct

from databases.qdrant.collections import COLLECTION_NAME
from databases.qdrant.config import get_qdrant_client
from exceptions.core import ErrorContext
from exceptions.databases import QdrantException
from schemas.corpus.qdrant import CorpusItem
from utils.decorators.exceptions import guard_async

# --- Internal helpers ---


def _to_point_struct(
	item: CorpusItem,
) -> PointStruct:
	"""
	Converts a CorpusItem to a PointStruct for
	insertion into QdrantDB.
	"""
	return PointStruct(
		id=item.id,
		vector=item.vector,
		payload={
			'type': item.payload.type,
			'schema_version': item.payload.schema_version,
			'entity_id': item.payload.entity_id,
		},
	)


# --- Point Creation ---


@guard_async(
	operation='create_points',
	component='qdrant.points',
	code='point_creation_error',
	wrap_cls=QdrantException,
)
async def create_points(
	items: list[CorpusItem],
	collection_name: str = COLLECTION_NAME,
) -> None:
	"""
	Creates points in the specified Qdrant collection
	from a list of CorpusItem objects.
	"""
	client = get_qdrant_client()
	points = [_to_point_struct(item) for item in items]
	try:
		await client.upsert(
			collection_name=collection_name,
			points=points,
		)
	except Exception as e:
		raise QdrantException(
			message=(
				f'Failed to create points in collection '
				f'"{collection_name}".'
			),
			code='point_creation_failed',
			context=ErrorContext(
				operation='create_points',
				component='qdrant.points',
				metadata={
					'collection_name': collection_name
				},
			),
			cause=e,
		) from e


# --- Point Deletion ---


@guard_async(
	operation='delete_points_by_id',
	component='qdrant.points',
	code='point_deletion_error',
	wrap_cls=QdrantException,
)
async def delete_points_by_id(
	point_ids: list[str],
	collection_name: str = COLLECTION_NAME,
) -> None:
	"""
	Deletes points from the specified Qdrant collection
	by their IDs.
	"""
	client = get_qdrant_client()
	try:
		ids = cast(list[ExtendedPointId], list(point_ids))
		selector = PointIdsList(points=ids)
		await client.delete(
			collection_name=collection_name,
			points_selector=selector,
		)
	except Exception as e:
		raise QdrantException(
			message=(
				f'Failed to delete points from collection '
				f'"{collection_name}".'
			),
			code='point_deletion_failed',
			context=ErrorContext(
				operation='delete_points_by_id',
				component='qdrant.points',
				metadata={
					'collection_name': collection_name,
					'point_ids': point_ids,
				},
			),
			cause=e,
		) from e
