"""
This module defines the dispatch mechanism for the agent's
tools, allowing the agent to call various tools based on the
current context and needs during interactions.
"""

import asyncio
from typing import Any

import sentry_sdk

from agent.prompts.tools import (
	return_failed_tool_response,
	return_successful_tool_response,
)
from agent.tools.corpus_lookup import corpus_lookup
from agent.tools.faq_list import form_faq_tool_response
from events.lifecycle import publish_websocket_message
from i18n.swahili import translate_to_swahili
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.api.responses import WebSocketMessageType
from schemas.users.core import LanguagePreference
from users.service.retrieval import get_anonymous_user

# --- Constants ---

_TRANSLATION_TIMEOUT = 6.0

# --- Helper functions ---


async def _translate_tool_titles(
	user_id: str,
	titles: list[str],
) -> list[str]:
	user = await get_anonymous_user(user_id)

	if (
		not user
		or user.language_preference != LanguagePreference.SWAHILI
	):
		return titles

	try:
		results = await asyncio.wait_for(
			asyncio.gather(
				*(translate_to_swahili(t) for t in titles),
				return_exceptions=True,
			),
			timeout=_TRANSLATION_TIMEOUT,
		)
	except Exception:
		return titles

	return [
		orig if isinstance(res, BaseException) else res
		for orig, res in zip(titles, results, strict=True)
	]


async def _send_tool_ws_message(
	user_id: str,
	tool_name: str,
	titles: list[str],
	connection_id: str | None = None,
) -> None:
	"""
	Utility function to send a tool message event
	to the frontend via WebSocket.
	"""
	# Translate titles if user prefers Swahili
	titles = await _translate_tool_titles(user_id, titles)

	message = (
		f'Sending the following titles '
		f'for tool {tool_name}:\n'
		f'{", ".join(titles)}'
	)
	payload = {
		'tool_name': tool_name,
		'titles': titles,
	}
	await publish_websocket_message(
		user_id=user_id,
		message_type=WebSocketMessageType.TOOL_MESSAGE,
		payload=payload,
		message=message,
		event_options=(
			{'connection_id': connection_id}
			if connection_id
			else None
		),
	)


async def _send_faq_ws_message(
	user_id: str,
	connection_id: str | None = None,
) -> None:
	"""
	Utility function to send a FAQ tool message event
	to the frontend via WebSocket.
	"""
	await _send_tool_ws_message(
		user_id=user_id,
		tool_name='faq_list',
		titles=['Searching frequently asked questions'],
		connection_id=connection_id,
	)


async def _send_corpus_lookup_ws_message(
	user_id: str,
	query: str,
	type_filter: str,
	connection_id: str | None = None,
) -> None:
	"""
	Utility function to send a corpus lookup tool message event
	to the frontend via WebSocket.
	"""
	filter_title = (
		f'Filtering by type: {type_filter}'
		if type_filter != 'any'
		else 'No type filter applied'
	)
	query_title = f'Searching under: {query}'
	await _send_tool_ws_message(
		user_id=user_id,
		tool_name='corpus_lookup',
		titles=[
			'Performing corpus lookup',
			filter_title,
			query_title,
		],
		connection_id=connection_id,
	)


# --- Main dispatch function ---


async def dispatch_tool_call(
	user_id: str,
	tool_name: str,
	tool_args: dict[str, Any],
	user_input: str,
	connection_id: str | None = None,
) -> str:
	"""
	Dispatches the tool call to the appropriate tool function
	based on the tool name and arguments provided.
	"""
	try:
		if tool_name == 'faq_list':
			# Send initial WebSocket message to
			# indicate FAQ search
			await _send_faq_ws_message(
				user_id=user_id, connection_id=connection_id
			)
			result = await form_faq_tool_response()
			return return_successful_tool_response(
				tool_name=tool_name,
				tool_response=result,
			)
		elif tool_name == 'corpus_lookup':
			# Send initial WebSocket message to indicate
			# corpus lookup
			query = tool_args.get('query', user_input)
			type_filter = tool_args.get('type_filter', 'any')
			await _send_corpus_lookup_ws_message(
				user_id=user_id,
				query=query,
				type_filter=type_filter,
				connection_id=connection_id,
			)
			result = await corpus_lookup(
				query=query, type_filter=type_filter
			)
			return return_successful_tool_response(
				tool_name=tool_name,
				tool_response=result,
			)
		else:
			raise ValueError(f'Unknown tool: {tool_name}')
	except Exception as e:
		add_breadcrumb(
			category='agent.tools.dispatch_tool_call',
			message=f'Tool call failed: {tool_name}',
			level=BreadcrumbLevel.ERROR,
			data={'error': str(e), 'tool_args': tool_args},
		)
		sentry_sdk.capture_exception(e)
		return return_failed_tool_response(
			tool_name=tool_name,
		)
