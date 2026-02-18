"""MongoDB connection test"""

from databases.mongodb.config import (
	is_mongodb_connected,
)


async def test_mongodb_connection():
	"""
	Test connection to MongoDB
	for the AI Engine.
	"""
	assert await is_mongodb_connected() is True
