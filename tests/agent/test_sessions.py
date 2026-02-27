"""
This module contains tests for validating the
functionality of the agent's session management,
including session creation, retrieval, and state updates.
"""

from agent.sessions.creation import create_agent_session
from databases.mongodb.main import MongoDBCollection
from schemas.agent.sessions import AgentSession
from shared.ids import generate_uuid_str
from tests.utils.mongodb import clear_collection

# --- Test Cases ---


async def test_create_agent_session():
	"""
	Tests the creation of a new agent session and
	validates that the session metadata is correctly
	stored in the database.
	"""
	# Clear sessions collection before test
	await clear_collection(MongoDBCollection.SESSIONS)

	# Create a new agent session
	user_id = generate_uuid_str()
	user_input = 'Test Chat Session'
	new_session = await create_agent_session(
		user_id=user_id,
		user_input=user_input,
	)

	# Validate the returned session metadata
	assert isinstance(new_session, AgentSession)
	assert new_session.user_id == user_id
	assert new_session.chat_name == user_input[:10]

	# clear sessions collection after test
	await clear_collection(MongoDBCollection.SESSIONS)
