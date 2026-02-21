"""
This module defines the dispatch mechanism for the agent's
tools, allowing the agent to call various tools based on the
current context and needs during interactions.
"""

from typing import Any

import sentry_sdk

from agent.prompts.tools import (
	return_failed_tool_response,
	return_successful_tool_response,
)
from agent.tools.corpus_lookup import corpus_lookup
from agent.tools.faq_list import form_faq_tool_response
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)


async def dispatch_tool_call(
	tool_name: str,
	tool_args: dict[str, Any],
	user_input: str,
) -> str:
	"""
	Dispatches the tool call to the appropriate tool function
	based on the tool name and arguments provided.
	"""
	try:
		if tool_name == 'faq_list':
			# TODO: Send tool message in loading state
			# before processing
			result = await form_faq_tool_response()
			return return_successful_tool_response(
				tool_name=tool_name,
				tool_response=result,
			)
		elif tool_name == 'corpus_lookup':
			# TODO: Send tool message in loading state
			# before processing
			query = tool_args.get('query', user_input)
			type_filter = tool_args.get('type_filter', 'any')
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
