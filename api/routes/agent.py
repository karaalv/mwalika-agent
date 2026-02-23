"""
This module contains agent-related API routes,
such as agent interactions, agent session management,
and other agent-related functionalities.
"""

from fastapi import (
	APIRouter,
	Depends,
	Request,
	WebSocket,
	WebSocketDisconnect,
)

from agent.main import agent_chat
from agent.memory.retrieval import retrieve_agent_memory
from agent.sessions.deletion import delete_agent_session
from api.dependencies.ratelimit import require_access_and_rate_limit
from api.lifecycle.websocket_registry import (
	add_websocket_connection,
	remove_websocket_connection,
)
from api.utils.responses import (
	create_websocket_response,
	http_response,
)
from authorisation.jwt.create import create_token
from events.lifecycle import publish_event
from schemas.api.requests import (
	WebSocketRequest,
	WebSocketRequestType,
)
from schemas.api.responses import WebSocketMessageType
from schemas.events.core import EventType
from security.ratelimit.policies import ResourcePolicyType
from shared.ids import generate_uuid_str
from shared.tokens import count_tokens
from users.service.creation import create_anonymous_user
from users.service.update import (
	increment_user_agent_input_tokens,
	increment_user_requests,
)

# --- Router setup ---

agent_router = APIRouter()

# --- API routes ---

# Session management routes


@agent_router.delete('/session/{session_id}')
async def delete_session(
	request: Request,
	session_id: str,
	user_id: str = Depends(
		require_access_and_rate_limit(
			ResourcePolicyType.AGENT_INTERACTION
		)
	),
):
	"""
	API endpoint to delete an agent session
	and all associated data.
	"""
	request_id = getattr(request.state, 'request_id', '')
	await delete_agent_session(session_id)

	# Increment user request count
	# for usage stats
	if user_id:
		await increment_user_requests(user_id=user_id)

	return http_response(
		request_id=request_id,
		success=True,
		message=(f'Agent session {session_id} deleted successfully'),
	)


@agent_router.get('/session/{session_id}/memory')
async def get_session_memory(
	request: Request,
	session_id: str,
	user_id: str = Depends(
		require_access_and_rate_limit(
			ResourcePolicyType.AGENT_INTERACTION
		)
	),
):
	"""
	API endpoint to retrieve all memory entries
	associated with a specific agent session.
	"""
	request_id = getattr(request.state, 'request_id', '')

	if not user_id:
		return http_response(
			request_id=request_id,
			success=False,
			message='User ID not found in cookies',
			status_code=400,
		)

	memory_entries = await retrieve_agent_memory(
		session_id=session_id,
		user_id=user_id,
	)

	# Increment user request count for usage stats
	await increment_user_requests(user_id=user_id)

	return http_response(
		request_id=request_id,
		success=True,
		message=(
			f'Memory entries for session {session_id} '
			f'retrieved successfully'
		),
		data=memory_entries,
	)


# Agent interaction routes


@agent_router.websocket('/ws/chat/')
async def agent_chat_websocket(
	websocket: WebSocket,
	user_id: str = Depends(
		require_access_and_rate_limit(
			ResourcePolicyType.AGENT_INTERACTION
		)
	),
):
	"""
	WebSocket endpoint for agent chat interactions.
	This endpoint receives messages from the client,
	processes them through the agent_chat function,
	and streams responses back to the client using the
	event bus as the communication channel.
	"""
	session_id = websocket.query_params.get('session_id')
	connection_id = generate_uuid_str()
	user_exists = bool(user_id)

	# If user ID is not set, create new
	# user once first message is received with
	# user input
	if not user_id:
		user_id = generate_uuid_str()
		user_exists = False

	# Start socket connection and
	# add to registry
	await websocket.accept()
	await add_websocket_connection(
		user_id=user_id,
		connection_id=connection_id,
		websocket=websocket,
	)

	# Main loop to receive messages
	try:
		while True:
			# TODO: Rate limit messages here
			data = await websocket.receive_json()
			ws_request = WebSocketRequest.model_validate(data)

			# Heartbeat handled by WebSocketManager,
			# so ignore here
			if ws_request.type == WebSocketRequestType.HEARTBEAT:
				continue
			# If agent interaction message,
			# process through agent_chat function
			elif (
				ws_request.type
				== WebSocketRequestType.AGENT_INTERACTION
			):
				user_input = ws_request.payload.message
				# create user if not exists, and send user ID
				# to client
				# TODO: validate user input, handle errors, etc.
				if not user_exists:
					await _create_user_send_event(
						user_id=user_id,
						connection_id=connection_id,
					)
					user_exists = True

				# Perform agent chat interaction,
				# which will publish events
				await agent_chat(
					user_id=user_id,
					session_id=session_id,
					user_input=user_input,
					connection_id=connection_id,
				)

				# Increment usage stats for user, etc.
				await increment_user_requests(user_id=user_id)
				await increment_user_agent_input_tokens(
					user_id=user_id,
					tokens=count_tokens(user_input),
				)
			else:
				# If unknown message type,
				# ignore or log as needed
				pass
	except WebSocketDisconnect:
		pass
	finally:
		await remove_websocket_connection(
			user_id=user_id,
			connection_id=connection_id,
			reason='WebSocket disconnected',
		)


# --- Agent utility functions ---


async def _create_user_send_event(
	user_id: str, connection_id: str
) -> None:
	"""
	Utility function to create an anonymous user and
	send a WebSocket message to the client with the
	new user ID and claim token.
	"""
	await create_anonymous_user(user_id=user_id)
	claim_token = create_token(
		sub=user_id,
		iss='mwalika-agent',
		typ='claim',
	)
	ws_response = create_websocket_response(
		request_id=generate_uuid_str(),
		success=True,
		message='Anonymous user created successfully',
		message_type=WebSocketMessageType.SET_USER_ID,
		payload={
			'user_id': user_id,
			'claim_token': claim_token,
		},
	)
	await publish_event(
		user_id=user_id,
		event_type=EventType.WEBSOCKET_MESSAGE,
		payload=ws_response,
		event_options={'connection_id': connection_id},
	)
