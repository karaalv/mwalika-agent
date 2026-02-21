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
from agent.streaming.stream_manager import (
	StreamManager,
	StreamParsingCode,
	StreamState,
)
from agent.tools.dispatch import dispatch_tool_call
from agent.tools.tool_definitions import TOOL_DEFINITIONS
from exceptions.core import (
	ApplicationException,
	ErrorContext,
)
from openai_client.main import agent_response_stream
from shared.ids import generate_uuid_str
from shared.logging import LogStyle, cprint
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
	tool_name: str,
	tool_args: dict[str, Any],
	user_input: str,
) -> str:
	"""
	Resolves the tool call by dispatching to the appropriate
	tool function based on the tool name and arguments.
	"""
	return await dispatch_tool_call(
		tool_name=tool_name,
		tool_args=tool_args,
		user_input=user_input,
	)


# --- Main Agent Functionality ---


@guard(
	operation='agent_chat',
	component='agent.main',
	code='agent_chat_error',
)
async def agent_chat(
	user_id: str,
	user_input: str,
	session_id: str | None = None,
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
		user_id=user_id, session_id=session_id, memory_id=memory_id
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
				pass
			elif event.item.type == 'message':
				# Handle message event
				state.set_state(StreamState.MESSAGE)
				pass
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
				# TODO: Send data to ws
				pass
		elif event.type == 'response.output_text.done':
			if state.get_state() == StreamState.MESSAGE:
				# Handle message text done event
				# Flush the stream manager buffer and return
				# any final content as needed
				remainder = state.flush_buffer()
				if verbosity_level > 0 and remainder:
					cprint(
						f'Message Remainder: {remainder.block}',
						style=LogStyle.DEFAULT,
					)
				# TODO: Send blocks to ws
				pass
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
				pass

	# If tool was called, execute the tool in recursive
	# agent_chat call and stream results back to user
	if state.get_state() == StreamState.TOOL and state.tool_name:
		tool_response = await _resolve_tool_call(
			tool_name=state.tool_name,
			tool_args=state.tool_args or {},
			user_input=user_input,
		)
		if verbosity_level > 0:
			cprint(
				f'Tool Response:\n\n{tool_response}',
				style=LogStyle.INFO,
			)
		# Recursively call agent_chat with tool response as input
		return await agent_chat(
			user_id=user_id,
			user_input=tool_response,
			session_id=session_id,
			recursion_instructions=recursion_instructions,
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

	state.clear_state()
