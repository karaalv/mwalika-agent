"""
This module contains logic for deleting agent sessions,
this includes deleting associated memory and any other
cleanup related to the session.
"""

from databases.mongodb.main import MongoDBCollection, get_collection


async def delete_agent_session(session_id: str) -> None:
	"""
	Deletes an agent session and all associated data.
	"""
	session_collection = get_collection(MongoDBCollection.SESSIONS)
	memory_collection = get_collection(MongoDBCollection.MEMORIES)
	# Delete the session document
	await session_collection.delete_one({'session_id': session_id})
	# Delete all memory entries associated with the session
	await memory_collection.delete_many({'session_id': session_id})
