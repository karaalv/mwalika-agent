"""
This module contains the main search logic for QdrantDB,
including vector search and filtering capabilities.
"""
from schemas.corpus.qdrant import CorpusItemType, CorpusSearchResult
from databases.qdrant.config import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue, ScoredPoint
from databases.qdrant.collections import COLLECTION_NAME
from exceptions.core import ErrorContext
from exceptions.databases import QdrantException
from utils.decorators.exceptions import guard_async

# --- Search helpers ---

def _type_filter(item_type: CorpusItemType) -> Filter:
    """
    Creates a Qdrant filter for the
    specified CorpusItemType.
    """
    return Filter(
        must=[
            FieldCondition(
                key='type',
                match=MatchValue(value=item_type.value),
            )
        ]
    )

def _package_result_item(
    result: ScoredPoint,
) -> CorpusSearchResult:
    """
    Converts a Qdrant search result item
    into a CorpusSearchResult.
    """
    tmp = {
        'id': result.id,
        'score': result.score,
        'payload': result.payload,
    }
    return CorpusSearchResult.model_validate(tmp)

# --- Search Functionality ---

@guard_async(
    operation='search_corpus',
    component='qdrant.search',
    code='corpus_search_error',
    wrap_cls=QdrantException,
)
async def search_corpus(
    query_vector: list[float],
    item_type: CorpusItemType,
    limit: int = 3,
    collection: str = COLLECTION_NAME,
) -> list[CorpusSearchResult]:
    """
    Performs a vector search on the Qdrant collection
    for items matching the specified type.
    """
    client = get_qdrant_client()
    try:
        search_result = await client.query_points(
            collection_name=collection,
            query_vector=query_vector,
            filter=_type_filter(item_type),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [
            _package_result_item(result)
            for result in search_result.points
        ]
    except Exception as e:
        raise QdrantException(
            message='Failed to perform corpus search.',
            code='corpus_search_failed',
            context=ErrorContext(
                operation='search_corpus',
                component='qdrant.search',
                metadata={
                    'item_type': item_type.value,
                    'limit': limit,
                },
            ),
            cause=e,
        ) from e