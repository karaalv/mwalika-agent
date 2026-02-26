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


class MongoDBDatabase(str, Enum):
	MWALIKA_CORPUS = 'mwalika_corpus'
	CHATS = 'chats'
	MWALIKA_IDENTITY = 'mwalika_identity'
	MWALIKA_SECURITY = 'mwalika_security'


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

	# Collections for Mwalika Identity database
	USERS = 'users'

	# Collections for Mwalika Security database
	USER_USAGE_STATS = 'user_usage_stats'
	IP_USAGE_STATS = 'ip_usage_stats'
	BLOCKED_ENTITIES = 'blocked_entities'


# Mapping between collection and
# database names for MongoDB operations
_collection_map: dict[MongoDBCollection, MongoDBDatabase] = {
	# Mwalika Corpus database
	MongoDBCollection.MINISTRIES: MongoDBDatabase.MWALIKA_CORPUS,
	MongoDBCollection.DEPARTMENTS: MongoDBDatabase.MWALIKA_CORPUS,
	MongoDBCollection.AGENCIES: MongoDBDatabase.MWALIKA_CORPUS,
	MongoDBCollection.SERVICES: MongoDBDatabase.MWALIKA_CORPUS,
	MongoDBCollection.FAQS: MongoDBDatabase.MWALIKA_CORPUS,
	# Chats database
	MongoDBCollection.SESSIONS: MongoDBDatabase.CHATS,
	MongoDBCollection.MEMORIES: MongoDBDatabase.CHATS,
	# Mwalika Identity database
	MongoDBCollection.USERS: MongoDBDatabase.MWALIKA_IDENTITY,
	# Mwalika Security database
	MongoDBCollection.USER_USAGE_STATS: (
		MongoDBDatabase.MWALIKA_SECURITY
	),
	MongoDBCollection.IP_USAGE_STATS: (
		MongoDBDatabase.MWALIKA_SECURITY
	),
	MongoDBCollection.BLOCKED_ENTITIES: (
		MongoDBDatabase.MWALIKA_SECURITY
	),
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
				metadata={'collection_name': collection.value},
			),
		)
	db_name = _collection_map[collection].value
	client = get_mongodb_client()
	return client[db_name][collection.value]
