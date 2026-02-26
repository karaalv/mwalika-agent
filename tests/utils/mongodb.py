"""
This module contains testing utilities for
mongodb interactions, namely creating and
tearing down test databases and collections for
agent session management.
"""

from databases.mongodb.config import (
	get_mongodb_client,
)
from databases.mongodb.main import (
	MongoDBCollection,
	MongoDBDatabase,
	get_collection,
)


async def clear_collection(collection: MongoDBCollection) -> None:
	"""
	Clears all documents from the specified
	MongoDB collection.
	"""
	coll = get_collection(collection)
	await coll.delete_many({})


async def clear_test_databases() -> None:
	"""
	Clears all relevant databases and collections
	used for testing. Maintains the Mwalika Corpus
	database.
	"""
	client = get_mongodb_client()
	for db in MongoDBDatabase:
		if db == MongoDBDatabase.MWALIKA_CORPUS:
			continue
		await client.drop_database(db.value)
