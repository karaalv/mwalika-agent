"""
MongoDB entry point for collection access.

This module provides a single place to resolve
database and collection names for MongoDB usage.
"""

from enum import Enum

from pymongo.asynchronous.collection import AsyncCollection

from databases.mongodb.config import get_mongodb_client
from exceptions.core import ErrorContext
from exceptions.databases import MongoDBException

# --- Configuration ---


class MongoDBCollection(str, Enum):
	# Collections for Mwalika Corpus database
	MINISTRIES = 'ministries'
	DEPARTMENTS = 'departments'
	AGENCIES = 'agencies'
	SERVICES = 'services'
	FAQS = 'faqs'

	# Collections for Chats database
	SESSIONS = 'sessions'
	MEMORIES = 'memories'


# Mapping between collection and
# database names for MongoDB operations
_collection_map: dict[MongoDBCollection, str] = {
	# Mwalika Corpus database
	MongoDBCollection.MINISTRIES: 'mwalika_corpus',
	MongoDBCollection.DEPARTMENTS: 'mwalika_corpus',
	MongoDBCollection.AGENCIES: 'mwalika_corpus',
	MongoDBCollection.SERVICES: 'mwalika_corpus',
	MongoDBCollection.FAQS: 'mwalika_corpus',
	# Chats database
	MongoDBCollection.SESSIONS: 'chats',
	MongoDBCollection.MEMORIES: 'chats',
}

# --- Collection Access ---


async def get_collection(
	collection: MongoDBCollection,
) -> AsyncCollection:
	"""
	Retrieves a MongoDB collection by name.
	"""
	if collection not in _collection_map:
		raise MongoDBException(
			message=(
				f'Collection "{collection.value}" is not '
				'defined in the collection map.'
			),
			code='collection_not_defined',
			context=ErrorContext(
				operation='get_collection',
				component='mongodb.main',
				metadata={
					'collection_name': collection.value
				},
			),
		)
	db_name = _collection_map[collection]
	client = get_mongodb_client()
	return client[db_name][collection.value]
