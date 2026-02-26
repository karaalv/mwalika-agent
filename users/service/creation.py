"""
This module contains logic for creating anonymous
users in the Mwalika Agent system, including generating
unique user IDs and initializing user data.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.users.core import AnonymousUser


async def create_anonymous_user(user_id: str) -> AnonymousUser:
	"""
	Creates a new anonymous user with a unique user ID and
	initializes their usage statistics.
	"""

	# Create the anonymous user object
	anonymous_user = AnonymousUser(user_id=user_id)

	# Insert the anonymous user into the
	# database, note that usage stats will be
	# created on demand via the user observer
	users_collection = await get_collection(MongoDBCollection.USERS)
	await users_collection.insert_one(
		anonymous_user.model_dump(mode='json')
	)

	return anonymous_user
