"""
This module contains agent-related API routes,
such as agent interactions, agent session management,
and other agent-related functionalities.
"""

from typing import Any

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
from api.config.settings import (
	WS_MESSAGE_RATE_LIMIT_TIMEOUT_SECONDS,
)
from api.dependencies.ratelimit import (
	require_access_and_rate_limit,
	ws_require_access_and_rate_limit,
)
from api.dependencies.timeouts import (
	timeout_limiter_ws,
)
from api.guards.agent.routes import (
	guard_agent_websocket_connection,
	guard_agent_websocket_data,
	guard_agent_websocket_disconnection,
	guard_agent_websocket_input_content,
)
from api.lifecycle.websocket_registry import (
	add_websocket_connection,
	remove_websocket_connection,
)
from api.utils.ip_addresses import get_ws_ip
from api.utils.responses import (
	create_websocket_response,
	http_response,
)
from api.utils.tokens import generate_claim_token
from events.lifecycle import (
	publish_event,
	publish_websocket_message,
)
from schemas.api.requests import (
	WebSocketRequest,
	WebSocketRequestType,
)
from schemas.api.responses import (
	WebSocketMessageType,
)
from schemas.events.core import EventType
from security.ratelimit.policies import (
	ResourcePolicyIdentifierType,
	ResourcePolicyType,
)
from security.ratelimit.store import get_limiter
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
	payload: dict[str, Any] = Depends(  # noqa: B008
		require_access_and_rate_limit(  # noqa: B008
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

	return http_response(
		request_id=request_id,
		success=True,
		message=(f'Agent session {session_id} deleted successfully'),
	)


@agent_router.get('/session/{session_id}/memory')
async def get_session_memory(
	request: Request,
	session_id: str,
	payload: dict[str, Any] = Depends(  # noqa: B008
		require_access_and_rate_limit(  # noqa: B008
			ResourcePolicyType.AGENT_INTERACTION
		)
	),
):
	"""
	API endpoint to retrieve all memory entries
	associated with a specific agent session.
	"""
	request_id = getattr(request.state, 'request_id', '')
	user_id = payload.get('sub', '')

	if not user_id:
		return http_response(
			request_id=request_id,
			success=False,
			message='User ID not found in token payload',
			status_code=400,
		)

	memory_entries = await retrieve_agent_memory(
		session_id=session_id,
		user_id=user_id,
	)

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
	payload: dict[str, Any] = Depends(  # noqa: B008
		ws_require_access_and_rate_limit(  # noqa: B008
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
	ip_address = get_ws_ip(websocket)
	user_id = payload.get('sub', '')
	token_id = payload.get('jti', '')
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

	# Guard the WebSocket connection for this
	# user and IP address
	await guard_agent_websocket_connection(
		ip_address=ip_address,
		user_id=user_id,
		connection_id=connection_id,
	)

	# Only add connection to registry after passing guards
	await add_websocket_connection(
		user_id=user_id,
		connection_id=connection_id,
		websocket=websocket,
	)

	# Get rate limiter instances for this
	# connection
	limiter = await get_limiter(
		policy_type=ResourcePolicyType.AGENT_MESSAGING,
		identifier_type=ResourcePolicyIdentifierType.USER,
		identifier_value=user_id,
	)
	timeout = WS_MESSAGE_RATE_LIMIT_TIMEOUT_SECONDS
	timeout_limiter = timeout_limiter_ws(
		limiter=limiter,
		timeout_seconds=timeout,
		websocket=websocket,
	)

	# Main loop to receive messages
	try:
		while True:
			# Rate limit user messages
			if not limiter.has_capacity:
				message = (
					'Rate limit exceeded: Too many messages. '
					'Please wait before sending more.'
				)
				await publish_websocket_message(
					message=message,
					payload=message,
					user_id=user_id,
					connection_id=connection_id,
					message_type=WebSocketMessageType.WARNING,
					success=False,
				)
				continue

			async with timeout_limiter:
				data = await websocket.receive_json()

				# Guard against excessively large messages
				await guard_agent_websocket_data(
					ip_address=ip_address,
					token_id=token_id,
					user_id=user_id,
					connection_id=connection_id,
					data=data,
				)

				# Process message based on type
				ws_request = WebSocketRequest.model_validate(data)

				# Heartbeat handled by WebSocketManager,
				# so ignore here
				if ws_request.type == WebSocketRequestType.HEARTBEAT:
					continue
				elif (
					ws_request.type
					== WebSocketRequestType.AGENT_INTERACTION
				):
					user_input = ws_request.payload.message

					# Guard against excessively long input messages
					await guard_agent_websocket_input_content(
						ip_address=ip_address,
						token_id=token_id,
						user_id=user_id,
						connection_id=connection_id,
						user_input=user_input,
					)

					# create user if not exists, and send user ID
					# to client for future interactions
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
				else:
					# If unknown message type,
					# ignore or log as needed
					pass
	except WebSocketDisconnect:
		pass
	finally:
		# Guard the WebSocket disconnection - currently
		# no real logic is implemented here, this removes
		# the connection info from observers
		await guard_agent_websocket_disconnection(
			ip_address=ip_address,
			user_id=user_id,
			connection_id=connection_id,
		)
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
	claim_token = generate_claim_token(user_id=user_id)
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
