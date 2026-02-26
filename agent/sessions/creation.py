"""
This module contains logic for managing
the creation of new agent sessions.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.agent.sessions import AgentSession
from shared.ids import generate_uuid_str

# --- Constants ---

_INPUT_SESSION_NAME_MAX_LENGTH = 10


async def create_agent_session(
	user_id: str,
	user_input: str,
) -> AgentSession:
	"""
	Creates a new agent session in the database and returns
	the session metadata.
	"""
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	new_session = AgentSession(
		session_id=generate_uuid_str(),
		user_id=user_id,
		chat_name=user_input[:_INPUT_SESSION_NAME_MAX_LENGTH],
	)
	await sessions_collection.insert_one(
		new_session.model_dump(mode='json')
	)
	return new_session
