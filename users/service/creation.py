"""
This module contains logic for creating anonymous
users in the Mwalika Agent system, including generating
unique user IDs and initializing user data.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.users.core import AnonymousUser
from schemas.users.security import UserUsageStats


async def create_anonymous_user(user_id: str) -> AnonymousUser:
	"""
	Creates a new anonymous user with a unique user ID and
	initializes their usage statistics.
	"""

	# Create the anonymous user object
	anonymous_user = AnonymousUser(user_id=user_id)

	# Initialize usage stats for the new user
	usage_stats = UserUsageStats(user_id=user_id)

	# Insert the anonymous user and their
	# usage stats into the database
	users_collection = await get_collection(MongoDBCollection.USERS)
	usage_stats_collection = await get_collection(
		MongoDBCollection.USER_USAGE_STATS
	)
	await users_collection.insert_one(
		anonymous_user.model_dump(mode='json')
	)
	await usage_stats_collection.insert_one(
		usage_stats.model_dump(mode='json')
	)

	return anonymous_user
