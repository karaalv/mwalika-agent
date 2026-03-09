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
from schemas.agent.sessions import AgentSession
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
	token_res = generate_access_token(user_id=user_id)
	access_token = token_res.token

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


async def test_agent_get_session_by_id_success(
	http_client: AsyncClient,
):
	"""
	Test the /agent/session/{session_id} endpoint to ensure it returns
	the correct session metadata when accessed with a valid session ID
	and access token.
	"""
	user_id = generate_uuid_str()

	# Create a test agent session
	test_session = await create_agent_session(
		user_id=user_id, user_input='Test Session'
	)

	# Generate an access token for the session
	token_res = generate_access_token(user_id=user_id)
	access_token = token_res.token

	# Make a request to the session retrieval
	# endpoint with the access token
	response = await http_client.get(
		f'/agent/session/{test_session.session_id}',
		headers={'Authorization': f'Bearer {access_token}'},
	)

	assert response.status_code == 200
	response_data = HttpApiResponse.model_validate(response.json())
	assert response_data.meta.success is True
	assert response_data.data is not None
	session = AgentSession.model_validate(response_data.data)
	assert session.session_id == test_session.session_id
	assert session.user_id == test_session.user_id

	# Clean up session after test
	await _clear_agent_sessions()


async def test_agent_get_sessions_for_user_success(
	http_client: AsyncClient,
):
	"""
	Test the /agent/sessions endpoint to ensure it returns
	the list of sessions for a user when accessed with a valid
	access token.
	"""
	user_id = generate_uuid_str()

	# Create multiple test agent sessions for the user
	session1 = await create_agent_session(
		user_id=user_id, user_input='Session 1'
	)
	session2 = await create_agent_session(
		user_id=user_id, user_input='Session 2'
	)

	# Generate an access token for the user
	token_res = generate_access_token(user_id=user_id)
	access_token = token_res.token

	# Make a request to the sessions retrieval endpoint
	response = await http_client.get(
		'/agent/sessions',
		headers={'Authorization': f'Bearer {access_token}'},
	)

	assert response.status_code == 200
	response_data = HttpApiResponse.model_validate(response.json())
	assert response_data.meta.success is True
	assert response_data.data is not None
	assert isinstance(response_data.data, list)
	assert len(response_data.data) >= 2
	sessions = [
		AgentSession.model_validate(item)
		for item in response_data.data
	]
	assert session1.session_id in [
		session.session_id for session in sessions
	]
	assert session2.session_id in [
		session.session_id for session in sessions
	]

	# Clean up sessions after test
	await _clear_agent_sessions()
