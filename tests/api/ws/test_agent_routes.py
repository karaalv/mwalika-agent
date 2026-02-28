"""
This module contains WebSocket tests for the agent-related API routes,
including tests for agent interactions, session management, and
other agent-related functionalities.
"""

import asyncio
import json
from typing import Any

import pytest
import websockets
from fastapi import status
from websockets import ClientConnection

from agent.sessions.creation import create_agent_session
from api.utils.tokens import generate_access_token, verify_claim_token
from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.api.requests import (
	WebSocketRequest,
	WebSocketRequestPayload,
	WebSocketRequestType,
)
from schemas.api.responses import (
	WebSocketMessagePayload,
	WebSocketMessageType,
	WebSocketResponse,
)
from security.config.agent import MAX_INPUT_LENGTH
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


def _create_ws_agent_message(
	message: str,
) -> WebSocketRequest:
	"""
	Utility function to create a WebSocketRequest message for testing
	the websocket routes.
	"""
	return WebSocketRequest(
		type=WebSocketRequestType.AGENT_INTERACTION,
		payload=WebSocketRequestPayload(message=message),
	)


async def _recv_websocket_message(
	ws: ClientConnection, timeout_s: float = 10.0
) -> WebSocketResponse:
	"""
	Utility function to receive a single message from a WebSocket
	connection with a timeout to prevent hanging tests.
	"""
	try:
		msg = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
		print(f'RECEIVED RAW WEBSOCKET MESSAGE: {msg}')
	except asyncio.TimeoutError:
		pytest.fail(
			f'WebSocket did not receive a '
			f'message within {timeout_s} seconds'
		)
	except websockets.ConnectionClosedOK:
		raise
	except websockets.ConnectionClosedError:
		raise
	except Exception:
		raise

	if isinstance(msg, (bytes, bytearray)):
		msg = msg.decode('utf-8', errors='replace')

	try:
		payload: Any = json.loads(msg)
	except json.JSONDecodeError:
		pytest.fail(f'Received invalid JSON message: {msg}')
		raise

	return WebSocketResponse.model_validate(payload)


async def _collect_ws_messages(
	ws: ClientConnection,
	max_messages: int = 300,
	timeout_s: float = 10.0,
) -> list[WebSocketResponse]:
	"""
	Utility function to collect all messages
	from a WebSocket connection until it is closed or a maximum
	number of messages is reached to prevent infinite loops in tests.
	"""
	messages: list[WebSocketResponse] = []
	for _ in range(max_messages):
		ws_response = await _recv_websocket_message(
			ws, timeout_s=timeout_s
		)
		messages.append(ws_response)
		if ws_response.message.type == WebSocketMessageType.AGENT_END:
			break
		if ws_response.message.type == WebSocketMessageType.ERROR:
			break
		if ws_response.message.type == WebSocketMessageType.WARNING:
			break

	# Filter out heartbeat messages
	messages = [
		msg
		for msg in messages
		if msg.message.type != WebSocketMessageType.HEARTBEAT
	]

	return messages


# --- Websocket Route Tests ---


async def test_agent_websocket_interaction_success(
	server_instance: str,
):
	"""
	Test the /agent/interact websocket endpoint to ensure it allows
	a client to interact with the agent and receive responses.
	"""
	user_id = generate_uuid_str()

	# Create a test agent session
	test_session = await create_agent_session(
		user_id=user_id, user_input='Test Session'
	)

	# Generate an access token for the session
	access_token = generate_access_token(user_id=user_id)

	# Connect to the websocket endpoint with the access token
	url = (
		f'/agent/ws/chat?'
		f'session_id={test_session.session_id}'
		f'&access_token={access_token}'
	)
	async with websockets.connect(
		f'ws://{server_instance}{url}'
	) as ws:
		# Send a test interaction message
		interaction_message = _create_ws_agent_message(
			'Hello, Agent!'
		)
		await ws.send(interaction_message.model_dump_json())

		# Collect messages from the websocket
		messages = await _collect_ws_messages(ws)

	# Assert start and end messages are typed correctly
	assert (
		messages[0].message.type == WebSocketMessageType.AGENT_START
	)
	assert messages[-1].message.type == WebSocketMessageType.AGENT_END

	agent_responses = [
		msg
		for msg in messages
		if msg.message.type == WebSocketMessageType.AGENT_RESPONSE
	]
	assert len(agent_responses) > 0

	# Clean up session and memory after test
	await _clear_agent_sessions()
	await _clear_agent_memory()


async def test_agent_websocket_interaction_unauthorized(
	server_instance: str,
):
	"""
	Test the /agent/interact websocket endpoint to ensure it rejects
	a client that tries to connect without a valid access token.
	"""

	# Attempt to connect to the websocket endpoint
	# without an access token
	url = f'ws://{server_instance}/agent/ws/chat'
	async with websockets.connect(url) as ws:
		# Check for error message
		response = await _collect_ws_messages(ws)
		assert len(response) == 1
		assert response[0].meta.success is False
		assert response[0].message.type == WebSocketMessageType.ERROR

		# Check that the connection is closed after the error message
		with pytest.raises(websockets.ConnectionClosed) as exc_info:
			await ws.recv()

		close_code = None
		if exc_info.value.rcvd is not None:
			close_code = exc_info.value.rcvd.code

		assert close_code == status.WS_1008_POLICY_VIOLATION


async def test_agent_websocket_create_user_on_interaction(
	server_instance: str,
):
	"""
	Test the /agent/interact websocket endpoint to ensure it creates
	a user and sends the user ID back to the client on the first
	interaction if the user does not already exist.
	"""

	# Generate an access token for the session
	access_token = generate_access_token()

	# Connect to the websocket endpoint with the access token
	url = f'ws://{server_instance}/agent/ws/chat?access_token={access_token}'
	async with websockets.connect(url) as ws:
		# Send a test interaction message
		interaction_message = _create_ws_agent_message(
			'Hello, Agent!'
		)
		await ws.send(interaction_message.model_dump_json())

		# Collect messages from the websocket
		messages = await _collect_ws_messages(ws)

	# Assert that a message containing the user ID
	# was sent back to the client
	user_id_messages = [
		msg
		for msg in messages
		if (msg.message.type == WebSocketMessageType.SET_USER_ID)
	]
	assert len(user_id_messages) == 1

	# Assert the user ID and claim token are included in the payload
	payload_raw: WebSocketMessagePayload = user_id_messages[
		0
	].message.payload

	assert isinstance(payload_raw, dict)
	payload: dict[str, Any] = payload_raw

	assert 'user_id' in payload
	assert payload['user_id'] is not None
	assert 'claim_token' in payload
	assert payload['claim_token'] is not None

	# Verify the claim token is valid and corresponds to the user ID
	claim_token = payload['claim_token']
	claim_token_payload = verify_claim_token(claim_token)
	assert claim_token_payload.get('sub') == payload['user_id']

	# Clean up session and memory after test
	await _clear_agent_sessions()
	await _clear_agent_memory()


async def test_agent_websocket_max_input_length_exceeded(
	server_instance: str,
):
	"""
	Test the /agent/interact websocket endpoint to ensure it properly
	rejects an interaction message that exceeds the maximum allowed
	input length.
	"""

	# Generate an access token for the session
	access_token = generate_access_token()

	# Connect to the websocket endpoint with the access token
	url = f'ws://{server_instance}/agent/ws/chat?access_token={access_token}'
	async with websockets.connect(url) as ws:
		# Send an interaction message that exceeds
		# the max input length
		long_message = 'A' * (MAX_INPUT_LENGTH + 1)
		interaction_message = _create_ws_agent_message(long_message)
		await ws.send(interaction_message.model_dump_json())

		# Check for warning message about input length
		messages = await _collect_ws_messages(ws)
		print(f'THE MESSAGES: {messages}')

		assert len(messages) == 1
		assert messages[0].meta.success is False
		assert (
			messages[0].message.type == WebSocketMessageType.WARNING
		)
