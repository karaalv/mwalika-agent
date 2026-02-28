"""
This module contains HTTP tests for the agent-related API routes,
including tests for agent interactions, session management, and
other agent-related functionalities.
"""

from httpx import AsyncClient

from agent.sessions.creation import create_agent_session
from api.utils.tokens import generate_access_token
from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.agent.memory import AgentMemory
from schemas.api.responses import (
	HttpApiResponse,
)
from shared.ids import generate_uuid_str

# --- Utility functions for tests ---


async def _clear_agent_sessions():
	"""
	Utility function to clear the agent sessions collection
	in the database before running tests to ensure a clean state.
	"""
	sessions_collection = get_collection(MongoDBCollection.SESSIONS)
	await sessions_collection.delete_many({})


async def _clear_agent_memory():
	"""
	Utility function to clear the agent memory collection
	in the database before running tests to ensure a clean state.
	"""
	memory_collection = get_collection(MongoDBCollection.MEMORIES)
	await memory_collection.delete_many({})


# --- HTTP Route Tests ---


async def test_agent_get_memory_success(http_client: AsyncClient):
	"""
	Test the /agent/memory endpoint to ensure it returns
	the agent's memory when accessed with a valid access token.
	"""
	user_id = generate_uuid_str()

	# Create a test agent session
	test_session = await create_agent_session(
		user_id=user_id, user_input='Test Session'
	)

	# Generate an access token for the session
	access_token = generate_access_token(user_id=user_id)

	# Make a request to the memory endpoint with the access token
	response = await http_client.get(
		f'/agent/session/{test_session.session_id}/memory',
		headers={'Authorization': f'Bearer {access_token}'},
	)

	assert response.status_code == 200
	response_data = HttpApiResponse.model_validate(response.json())
	assert response_data.meta.success is True
	assert response_data.data is not None
	assert isinstance(response_data.data, list)
	assert all(
		isinstance(item, AgentMemory) for item in response_data.data
	)

	# Clean up session and memory after test
	await _clear_agent_sessions()
	await _clear_agent_memory()
