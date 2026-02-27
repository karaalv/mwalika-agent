"""
This module acts as the main entry point
for the agent component of the Mwalika Agent
system.
"""

import json
from textwrap import dedent
from typing import Any

from agent.memory.insertion import (
	insert_agent_memory,
	insert_user_input_memory,
)
from agent.memory.retrieval import retrieve_agent_memory_prompt
from agent.prompts.agent import AGENT_SYSTEM_PROMPT
from agent.sessions.creation import create_agent_session
from agent.sessions.update import update_session_last_active
from agent.streaming.stream_manager import (
	StreamItem,
	StreamManager,
	StreamParsingCode,
	StreamState,
)
from agent.tools.dispatch import dispatch_tool_call
from agent.tools.tool_definitions import TOOL_DEFINITIONS
from events.lifecycle import publish_websocket_message
from exceptions.core import (
	ApplicationException,
	ErrorContext,
)
from openai_client.main import agent_response_stream
from schemas.api.responses import (
	WebSocketMessageType,
)
from shared.ids import generate_uuid_str
from shared.logging import LogStyle, cprint
from users.service.update import update_user_last_active
from utils.decorators.exceptions import guard

# --- Constants ---

_RECURSION_LIMIT = 3

# --- Helpers ---


def _raise_recursion_limit_exceeded() -> None:
	raise ApplicationException(
		message=dedent(
			"""
            Recursion limit exceeded. The agent has
            reached the maximum allowed recursion
            depth and cannot continue further to
            prevent infinite loops.
            """
		).strip(),
		code='recursion_limit_exceeded',
		context=ErrorContext(
			operation='agent_chat',
			component='agent.main',
			metadata={'recursion_limit': _RECURSION_LIMIT},
		),
	)


async def _resolve_tool_call(
	user_id: str,
	tool_name: str,
	tool_args: dict[str, Any],
	user_input: str,
	connection_id: str | None = None,
) -> str:
	"""
	Resolves the tool call by dispatching to the appropriate
	tool function based on the tool name and arguments.
	"""
	return await dispatch_tool_call(
		user_id=user_id,
		tool_name=tool_name,
		tool_args=tool_args,
		user_input=user_input,
		connection_id=connection_id,
	)


async def _publish_session_update(
	user_id: str, session_id: str, connection_id: str | None = None
) -> None:
	"""
	Utility function to publish a WebSocket message event
	to notify the client of a session update, such as
	session creation or deletion.
	"""
	payload = {'session_id': session_id}
	await publish_websocket_message(
		user_id=user_id,
		message_type=WebSocketMessageType.SET_SESSION_ID,
		payload=payload,
		message=f'Session {session_id} update',
		event_options=(
			{'connection_id': connection_id}
			if connection_id
			else None
		),
	)


async def _publish_agent_response(
	user_id: str,
	block: StreamItem,
	connection_id: str | None = None,
) -> None:
	"""
	Utility function to publish a WebSocket message event
	to send an agent response back to the client.
	"""
	await publish_websocket_message(
		user_id=user_id,
		message_type=WebSocketMessageType.AGENT_RESPONSE,
		payload=block,
		message=(
			f'Agent response update'
			f'id {block.memory_id}'
			f'seq {block.sequence_number}'
		),
		event_options=(
			{'connection_id': connection_id}
			if connection_id
			else None
		),
	)


# --- Main Agent Functionality ---

# TODO: There is some issue with the agents ability
# to cohesively carry a conversation across multiple turns,
# especially when tools are involved. Need to investigate
# whether this is an issue with the way memory is being
# retrieved and included in the system prompt, or if there
# is some other issue with the way the agent is processing
# the conversation history and tool calls.


@guard(
	operation='agent_chat',
	component='agent.main',
	code='agent_chat_error',
)
async def agent_chat(
	user_id: str,
	user_input: str,
	session_id: str | None = None,
	connection_id: str | None = None,
	recursion_instructions: str | None = None,
	recursion_depth: int = 0,
	verbosity_level: int = 0,
):
	"""
	Main function to handle agent chat interactions.
	It takes user input and streams responses from the
	OpenAI API, including tool calls and outputs.
	"""
	if recursion_depth > _RECURSION_LIMIT:
		_raise_recursion_limit_exceeded()

	# Create chat session if does not exist
	if not session_id:
		new_session = await create_agent_session(user_id, user_input)
		session_id = new_session.session_id
		# Stream session creation event to ws
		# for client to update session list, etc.
		await _publish_session_update(
			user_id=user_id,
			session_id=session_id,
			connection_id=connection_id,
		)

	# Push user input to memory
	if recursion_depth == 0:
		await insert_user_input_memory(
			session_id=session_id,
			user_id=user_id,
			user_input=user_input,
		)

	# Fetch relevant memory for session
	memory_prompt = await retrieve_agent_memory_prompt(
		session_id=session_id,
		user_id=user_id,
	)
	if verbosity_level > 0:
		cprint(
			f'Memory Prompt: {memory_prompt}',
			style=LogStyle.DEFAULT,
		)

	# Handle processing agent system prompt with
	# memory and any recursion instructions
	agent_system_prompt = (
		AGENT_SYSTEM_PROMPT
		+ '\n\nRelevant Memory:\n'
		+ memory_prompt
		+ '\n\n'
		+ (recursion_instructions or '')
	)

	# Create response stream for agent, maintaining
	# stream state for processing events and tool calls
	memory_id = generate_uuid_str()
	state = StreamManager(
		user_id=user_id,
		session_id=session_id,
		memory_id=memory_id,
		verbosity_level=verbosity_level,
	)
	response_stream = await agent_response_stream(
		system_prompt=agent_system_prompt,
		user_input=user_input,
		tools=TOOL_DEFINITIONS,
	)

	# Handle streaming events, including
	# tool calls and outputs, and send responses
	# back to the user with websocket
	async for event in response_stream:
		if verbosity_level > 1:
			cprint(
				f'Agent Event: {event}',
				style=LogStyle.DEFAULT,
			)

		# Resolve type of event and handle accordingly
		if event.type == 'response.output_item.added':
			if event.item.type == 'function_call':
				# Handle tool call event
				state.set_state(StreamState.TOOL)
			elif event.item.type == 'message':
				# Handle message event
				state.set_state(StreamState.MESSAGE)
		elif event.type == 'response.output_text.delta':
			if state.get_state() == StreamState.MESSAGE:
				# Handle message text delta event
				response = state.add_delta(event.delta)
				if verbosity_level > 0:
					if response.code == StreamParsingCode.PASSTHROUGH:
						cprint(
							f'Message Delta: {response.block}',
							style=LogStyle.DEFAULT,
						)
					elif response.code == StreamParsingCode.BLOCK:
						cprint(
							f'NDJSON: {response.block}',
							style=LogStyle.INFO,
						)
				if not response.block:
					continue
				# Send message delta update to ws
				await _publish_agent_response(
					user_id=user_id,
					block=response.block,
					connection_id=connection_id,
				)
		elif event.type == 'response.output_text.done':
			if state.get_state() == StreamState.MESSAGE:
				# Handle message text done event
				# Flush the stream manager buffer and return
				# any final content as needed
				remainder = state.flush_manager()
				if verbosity_level > 0 and remainder:
					cprint(
						f'Message Remainder: {remainder.block}',
						style=LogStyle.DEFAULT,
					)
				if remainder.block:
					# Send final message update to ws
					await _publish_agent_response(
						user_id=user_id,
						block=remainder.block,
						connection_id=connection_id,
					)
		elif event.type == 'response.output_item.done':
			if state.get_state() == StreamState.TOOL:
				# Handle tool call done event
				if event.item.type == 'function_call':
					tool_name: str = event.item.name
					tool_args: dict[str, Any] = json.loads(
						event.item.arguments
					)
					state.set_tool_call(tool_name, tool_args)

					if verbosity_level > 0:
						cprint(
							f'Tool Call: {tool_name}'
							f' with args {tool_args}',
							style=LogStyle.INFO,
						)

	# If tool was called, execute the tool in recursive
	# agent_chat call and stream results back to user
	if state.get_state() == StreamState.TOOL and state.tool_name:
		tool_response = await _resolve_tool_call(
			user_id=user_id,
			tool_name=state.tool_name,
			tool_args=state.tool_args or {},
			user_input=user_input,
			connection_id=connection_id,
		)
		if verbosity_level > 0:
			cprint(
				f'Tool Response:\n\n{tool_response}',
				style=LogStyle.INFO,
			)
		# Recursively call agent_chat with tool response as input
		return await agent_chat(
			user_id=user_id,
			user_input=user_input,
			session_id=session_id,
			connection_id=connection_id,
			recursion_instructions=tool_response,
			recursion_depth=recursion_depth + 1,
			verbosity_level=verbosity_level,
		)

	# Insert memory into database with session_id,
	# user_id, content, etc.
	memory = state.get_agent_memory()
	if verbosity_level > 0:
		cprint(
			f'Inserting memory: {memory}',
			style=LogStyle.INFO,
		)
	await insert_agent_memory(memory)

	# Update session last active timestamp, etc.
	await update_session_last_active(session_id=session_id)
	await update_user_last_active(user_id=user_id)

	state.clear_state()
