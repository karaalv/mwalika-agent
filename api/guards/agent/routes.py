"""
This module contains guards for agent routes in the
Mwalika Agent system. These guards are used to protect
certain API endpoints by enforcing the security policies
defined in the observers, such as blocking users, IP addresses, or
tokens that have been flagged for suspicious behavior or abuse.
"""

from typing import Any

from fastapi import WebSocketException, status

from api.guards.agent.checks import (
	check_add_ws_ip,
	check_add_ws_user,
	check_agent_input_tokens_at,
	check_agent_input_tokens_ip,
	check_agent_input_tokens_user,
	check_bad_request_ws_at,
	check_bad_request_ws_ip,
	check_bad_request_ws_user,
	check_remove_ws_ip,
	check_remove_ws_user,
)
from api.lifecycle.websocket_registry import (
	remove_websocket_connection,
)
from events.lifecycle import publish_websocket_message_event
from schemas.api.responses import WebSocketMessageType
from security.config.agent import (
	MAX_CONTENT_SIZE_BYTES,
	MAX_INPUT_LENGTH,
)
from shared.data import get_bytes
from shared.tokens import count_tokens

# --- WebSocket connection guards ---


async def guard_agent_websocket_connection(
	ip_address: str,
	user_id: str,
	connection_id: str,
) -> None:
	"""
	Guard function that checks if the given IP address or user ID has
	been flagged for suspicious behavior or abuse by the respective
	observers when adding a WebSocket connection, and raises
	WebSocketException if so.
	"""
	await check_add_ws_ip(
		ip_address=ip_address,
		user_id=user_id,
		connection_id=connection_id,
	)
	await check_add_ws_user(
		user_id=user_id,
		connection_id=connection_id,
	)


async def guard_agent_websocket_disconnection(
	ip_address: str,
	user_id: str,
	connection_id: str,
) -> None:
	"""
	Guard function that checks if the given IP address or user ID has
	been flagged for suspicious behavior or abuse by the respective
	observers when removing a WebSocket connection, and raises
	WebSocketException if so.
	"""
	await check_remove_ws_ip(
		ip_address=ip_address,
		user_id=user_id,
		connection_id=connection_id,
	)
	await check_remove_ws_user(
		user_id=user_id,
		connection_id=connection_id,
	)


# --- WebSocket message guards ---


async def _guard_bad_request_ws_message(
	ip_address: str,
	token_id: str,
	user_id: str,
	connection_id: str,
	context: str,
) -> None:
	"""
	Guard function that checks if the given WebSocket message data is
	malformed or invalid, and if so, publishes a WebSocket message
	event indicating the error and raises WebSocketException.
	"""
	await check_bad_request_ws_ip(
		ip_address=ip_address,
		user_id=user_id,
		connection_id=connection_id,
		context=context,
	)
	await check_bad_request_ws_user(
		user_id=user_id,
		connection_id=connection_id,
		context=context,
	)
	await check_bad_request_ws_at(
		token_id=token_id,
		user_id=user_id,
		connection_id=connection_id,
		context=context,
	)


async def guard_agent_websocket_data(
	ip_address: str,
	token_id: str,
	user_id: str,
	connection_id: str,
	data: Any,
) -> None:
	"""
	Guard function that checks if the given data exceeds the maximum
	allowed content size for agent interactions, and if so, publishes
	a WebSocket message event indicating the error and closes the
	WebSocket connection with an appropriate status code.
	"""
	if get_bytes(data) > MAX_CONTENT_SIZE_BYTES:
		message = (
			f'Message content too large. Max size is '
			f'{MAX_CONTENT_SIZE_BYTES} bytes.'
		)

		# First perform bad request check to determine if
		# user should be blocked for sending bad data, then publish
		# error message and close connection
		await _guard_bad_request_ws_message(
			ip_address=ip_address,
			token_id=token_id,
			user_id=user_id,
			connection_id=connection_id,
			context=message,
		)

		# Will only reach this point if message is bad
		# but user is not blocked, so publish error
		# message and close connection
		await publish_websocket_message_event(
			user_id=user_id,
			connection_id=connection_id,
			message=message,
			message_type=WebSocketMessageType.ERROR,
		)
		await remove_websocket_connection(
			user_id=user_id,
			connection_id=connection_id,
			reason='Content size limit exceeded',
			close_code=1009,
		)
		raise WebSocketException(
			code=status.WS_1009_MESSAGE_TOO_BIG,
			reason=message,
		)


async def guard_agent_websocket_input_content(
	ip_address: str,
	token_id: str,
	user_id: str,
	connection_id: str,
	user_input: str,
) -> None:
	# If input exceeds maximum length, send warning message
	# but do not perform blocking actions
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
		return

	# Perform token count checks, which may result in
	# blocking if limits are exceeded
	token_count = count_tokens(user_input)
	await check_agent_input_tokens_ip(
		ip_address=ip_address,
		user_id=user_id,
		connection_id=connection_id,
		token_count=token_count,
	)
	await check_agent_input_tokens_user(
		user_id=user_id,
		connection_id=connection_id,
		token_count=token_count,
	)
	await check_agent_input_tokens_at(
		token_id=token_id,
		user_id=user_id,
		connection_id=connection_id,
		token_count=token_count,
	)
