"""
This module contains logic for updating session information
in the Mwalika Agent system, specifically for updating
session activity timestamps and other relevant session data.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from shared.time import get_timestamp


async def update_session_last_active(session_id: str) -> None:
	"""
	Updates the last active timestamp of the
	session to the current time.
	"""
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	await sessions_collection.update_one(
		{'session_id': session_id},
		{'$set': {'last_active_at': get_timestamp()}},
	)


async def update_session_chat_name(
	session_id: str, chat_name: str
) -> None:
	"""
	Updates the chat name of the session for display purposes.
	"""
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	await sessions_collection.update_one(
		{'session_id': session_id},
		{'$set': {'chat_name': chat_name}},
	)
