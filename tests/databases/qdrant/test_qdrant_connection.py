"""Test QdrantDB connection"""

from databases.qdrant.config import (
	is_qdrant_connected,
)


async def test_qdrant_connection():
	"""
	Test connection to QdrantDB
	for the AI Engine.
	"""
	assert await is_qdrant_connected() is True
