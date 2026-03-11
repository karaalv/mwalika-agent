"""
This module contains logic for updating user information
in the Mwalika Agent system, specifically for updating
usage statistics and other relevant user data when they interact
with the system.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.users.core import LanguagePreference
from shared.time import get_timestamp


async def update_user_last_active(user_id: str) -> None:
	"""
	Update the last active timestamp for a given user.
	"""
	users_collection = get_collection(MongoDBCollection.USERS)
	await users_collection.update_one(
		{'user_id': user_id},
		{'$set': {'last_active_at': get_timestamp()}},
	)


async def update_user_language_preference(
	user_id: str, language: LanguagePreference
) -> None:
	"""
	Update the language preference for a given user.
	"""
	users_collection = get_collection(MongoDBCollection.USERS)
	await users_collection.update_one(
		{'user_id': user_id},
		{'$set': {'language_preference': language.value}},
	)
