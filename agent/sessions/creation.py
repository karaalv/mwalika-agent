"""
This module contains logic for managing
the creation of new agent sessions.
"""

from agent.sessions.retrieval import retrieve_agent_sessions_for_user
from databases.mongodb.main import MongoDBCollection, get_collection
from exceptions.core import ApplicationException, ErrorContext
from schemas.agent.sessions import AgentSession
from security.config.observers import MAX_AGENT_SESSIONS_PER_USER

# --- Constants ---

_INPUT_SESSION_NAME_MAX_LENGTH = 30


async def create_agent_session(
	user_id: str,
	session_id: str,
	user_input: str,
) -> AgentSession:
	"""
	Creates a new agent session in the database and returns
	the session metadata.
	"""
	# Check if user has exceeded max agent sessions
	existing_sessions = await retrieve_agent_sessions_for_user(
		user_id
	)
	if len(existing_sessions) >= MAX_AGENT_SESSIONS_PER_USER:
		raise ApplicationException(
			context=ErrorContext(
				operation='create_agent_session',
				component='agent.sessions.creation',
				metadata={
					'user_id': user_id,
					'existing_sessions': len(existing_sessions),
				},
			),
			message=(
				f'User {user_id} has exceeded '
				f'the maximum number of allowed '
				f'agent sessions ({MAX_AGENT_SESSIONS_PER_USER})'
			),
			code='MAX_AGENT_SESSIONS_EXCEEDED',
		)
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	new_session = AgentSession(
		session_id=session_id,
		user_id=user_id,
		chat_name=user_input[:_INPUT_SESSION_NAME_MAX_LENGTH],
	)
	await sessions_collection.insert_one(
		new_session.model_dump(mode='json')
	)
	return new_session
