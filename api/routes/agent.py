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
from api.dependencies.ratelimit import (
	require_access_and_rate_limit,
	ws_require_access_and_rate_limit,
)
from api.lifecycle.websocket_registry import (
	add_websocket_connection,
	remove_websocket_connection,
)
from api.utils.responses import (
	create_websocket_response,
	http_response,
)
from api.websocket.utils import publish_websocket_message_event
from authorisation.jwt.create import create_token
from events.lifecycle import publish_event
from schemas.api.requests import (
	WebSocketRequest,
	WebSocketRequestType,
)
from schemas.api.responses import (
	WebSocketMessageType,
)
from schemas.events.core import EventType
from security.config.agent import (
	MAX_CONTENT_SIZE_BYTES,
	MAX_INPUT_LENGTH,
)
from security.ratelimit.policies import (
	ResourcePolicyType,
)
from security.ratelimit.store import get_limiter
from shared.data import get_bytes
from shared.ids import generate_uuid_str
from users.service.creation import create_anonymous_user

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

	# TODO: Increment user request count
	# for usage stats

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

	# TODO: Increment user request count for usage stats

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


@agent_router.websocket(
	'/ws/chat/',
)
async def agent_chat_websocket(
	websocket: WebSocket,
	user_id: str = Depends(
		ws_require_access_and_rate_limit(
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
	# Dependency will have already verified access
	# token and applied the interaction rate limit

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

	# Get rate limiter instances for this
	# connection
	user_limiter = get_limiter(
		policy_type=ResourcePolicyType.AGENT_MESSAGING,
		identifier_type='user',
		identifier_value=user_id,
	)

	# Main loop to receive messages
	# TODO: IF user gets blocked while connection is open, need to
	# handle that case and close the connection or prevent further
	# messages from being processed until block expires, etc.
	try:
		while True:
			# Rate limit user messages
			if not user_limiter.has_capacity:
				await publish_websocket_message_event(
					user_id=user_id,
					connection_id=connection_id,
					message=(
						'Rate limit exceeded: Too many messages. '
						'Please wait before sending more.'
					),
					message_type=WebSocketMessageType.WARNING,
				)
				continue

			async with user_limiter:
				data = await websocket.receive_json()
				# Check content size to prevent abuse
				if get_bytes(data) > MAX_CONTENT_SIZE_BYTES:
					await publish_websocket_message_event(
						user_id=user_id,
						connection_id=connection_id,
						message=(
							'Message content too large. '
							f'Max size is {MAX_CONTENT_SIZE_BYTES} '
							'bytes.'
						),
						message_type=WebSocketMessageType.ERROR,
					)
					await remove_websocket_connection(
						user_id=user_id,
						connection_id=connection_id,
						reason='Content size limit exceeded',
						close_code=1009,
					)
					break

				# Process message based on type
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
					# to client for future interactions
					if not user_exists:
						await _create_user_send_event(
							user_id=user_id,
							connection_id=connection_id,
						)
						user_exists = True

					# Enforce maximum input length
					if len(user_input) > MAX_INPUT_LENGTH:
						await publish_websocket_message_event(
							user_id=user_id,
							connection_id=connection_id,
							message=(
								f'Input exceeds maximum length of '
								f'{MAX_INPUT_LENGTH} characters.'
							),
							message_type=WebSocketMessageType.WARNING,
						)
						continue

					# Perform agent chat interaction,
					# which will publish events
					await agent_chat(
						user_id=user_id,
						session_id=session_id,
						user_input=user_input,
						connection_id=connection_id,
					)

					# TODO: Increment usage stats for user, etc.
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
