"""
This module contains logic for retrieving user information
in the Mwalika Agent system, specifically for handling
requests to get user details, usage statistics, and other
relevant data when users interact with the system.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.users.core import AnonymousUser


async def get_anonymous_user(user_id: str) -> AnonymousUser | None:
	"""
	Retrieve an anonymous user from the database by their user ID.
	Returns the AnonymousUser object if found, or None if not found.
	"""
	users_collection = get_collection(MongoDBCollection.USERS)
	user_data = await users_collection.find_one({'user_id': user_id})
	if user_data:
		return AnonymousUser.model_validate(user_data)
	return None
