"""
This module contains checks used in the guards for
agent routes in the Mwalika Agent system. These checks are used to
enforce the security policies defined in the observers, such as
blocking users, IP addresses, or tokens that have been flagged for
suspicious behavior or abuse.
"""

from fastapi import WebSocketException, status

from events.lifecycle import publish_websocket_message
from schemas.api.responses import WebSocketMessageType
from security.lifecycle import (
	get_ip_observer,
	get_token_observer,
	get_user_observer,
)

# --- Utils ---


async def _publish_block_message_and_close_websocket(
	user_id: str,
	connection_id: str,
	reason: str,
	code: int = status.WS_1008_POLICY_VIOLATION,
) -> None:
	"""
	Utility function that publishes a WebSocket message event
	indicating the block reason and closes the WebSocket connection
	with an appropriate status code.
	"""
	await publish_websocket_message(
		user_id=user_id,
		connection_id=connection_id,
		message=reason,
		payload=reason,
		message_type=WebSocketMessageType.ERROR,
		success=False,
	)
	raise WebSocketException(
		code=code,
		reason=reason,
	)


# --- Adding websocket connections ---


async def check_add_ws_ip(
	ip_address: str,
	user_id: str,
	connection_id: str,
) -> None:
	"""
	Checks if the given IP address has been flagged for suspicious
	behavior or abuse by the IP observer when adding a WebSocket
	connection, and raises WebSocketException if so.
	"""
	ip_observer = get_ip_observer()
	blocked_entity = await ip_observer.add_ws_connection(
		ip_address,
		connection_id,
	)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=blocked_entity.reason,
		)


async def check_add_ws_user(
	user_id: str,
	connection_id: str,
) -> None:
	"""
	Checks if the given user ID has been flagged for suspicious
	behavior or abuse by the user observer when adding a WebSocket
	connection, and raises WebSocketException if so.
	"""
	user_observer = get_user_observer()
	blocked_entity = await user_observer.add_ws_connection(
		user_id,
		connection_id,
	)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=blocked_entity.reason,
		)


# --- Removing websocket connections ---


async def check_remove_ws_ip(
	ip_address: str,
	user_id: str,
	connection_id: str,
) -> None:
	"""
	Checks if the given IP address has been flagged for suspicious
	behavior or abuse by the IP observer when removing a WebSocket
	connection, and raises WebSocketException if so.
	"""
	ip_observer = get_ip_observer()
	await ip_observer.remove_ws_connection(
		ip_address,
		connection_id,
	)


async def check_remove_ws_user(
	user_id: str,
	connection_id: str,
) -> None:
	"""
	Checks if the given user ID has been flagged for suspicious
	behavior or abuse by the user observer when removing a WebSocket
	connection, and raises WebSocketException if so.
	"""
	user_observer = get_user_observer()
	await user_observer.remove_ws_connection(
		user_id,
		connection_id,
	)


# --- Bad request checks ---


async def check_bad_request_ws_ip(
	ip_address: str,
	user_id: str,
	connection_id: str,
	context: str,
) -> None:
	ip_observer = get_ip_observer()
	blocked_entity = await ip_observer.add_bad_request(ip_address)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=(
				f'Reason: {blocked_entity.reason} '
				f'(Context: {context})'
			),
		)


async def check_bad_request_ws_at(
	token_id: str,
	user_id: str,
	connection_id: str,
	context: str,
) -> None:
	token_observer = get_token_observer()
	blocked_entity = await token_observer.add_at_bad_request(
		token_id,
	)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=(
				f'Reason: {blocked_entity.reason} '
				f'(Context: {context})'
			),
		)


async def check_bad_request_ws_user(
	user_id: str,
	connection_id: str,
	context: str,
) -> None:
	user_observer = get_user_observer()
	blocked_entity = await user_observer.add_bad_request(user_id)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=(
				f'Reason: {blocked_entity.reason} '
				f'(Context: {context})'
			),
		)


# --- Agent input tokens checks ---


async def check_agent_input_tokens_ip(
	ip_address: str,
	user_id: str,
	connection_id: str,
	token_count: int,
) -> None:
	ip_observer = get_ip_observer()
	blocked_entity = await ip_observer.add_agent_input_tokens(
		ip_address,
		token_count,
	)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=blocked_entity.reason,
		)


async def check_agent_input_tokens_at(
	token_id: str,
	user_id: str,
	connection_id: str,
	token_count: int,
) -> None:
	token_observer = get_token_observer()
	blocked_entity = await token_observer.add_at_agent_input_tokens(
		token_id,
		token_count,
	)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=blocked_entity.reason,
		)


async def check_agent_input_tokens_user(
	user_id: str,
	connection_id: str,
	token_count: int,
) -> None:
	user_observer = get_user_observer()
	blocked_entity = await user_observer.add_agent_input_tokens(
		user_id,
		token_count,
	)
	if blocked_entity:
		await _publish_block_message_and_close_websocket(
			user_id=user_id,
			connection_id=connection_id,
			reason=blocked_entity.reason,
		)
