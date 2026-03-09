"""
This module contains logic for retrieving
agent session information from the database,
such as fetching session metadata.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.agent.sessions import AgentSession


async def retrieve_agent_session(
	session_id: str,
) -> AgentSession | None:
	"""
	Retrieves an agent session from the database
	based on the session ID. Returns the session
	metadata if found, or None if not found.
	"""
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	session_data = await sessions_collection.find_one(
		{'session_id': session_id}
	)
	if session_data:
		return AgentSession.model_validate(session_data)
	return None


async def retrieve_agent_sessions_for_user(
	user_id: str,
) -> list[AgentSession]:
	"""
	Retrieves all agent sessions associated with a specific user ID.
	Returns a list of session metadata objects.
	"""
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	cursor = sessions_collection.find({'user_id': user_id})
	sessions = []
	async for session_data in cursor:
		sessions.append(AgentSession.model_validate(session_data))
	return sessions
