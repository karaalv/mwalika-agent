"""
This module contains the stream management
logic for maintaining state and processing events from
the OpenAI API response stream in the main agent chat
function.
"""

import json
from typing import Any

import sentry_sdk

from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.agent.memory import (
	AgentMemory,
	MemoryContent,
	MemoryContentTypes,
)
from schemas.agent.stream import (
	NdJsonItem,
	NdJsonTypes,
	StreamParsingCode,
	StreamParsingResponse,
	StreamState,
)
from shared.logging import LogStyle, cprint

# TODO: Redo this entire thing to better handle the
# stream parsing and state


class StreamManager:
	"""
	Manages the state of the OpenAI response stream,
	including buffering and processing of events.
	"""

	def __init__(self, user_id: str, session_id: str, memory_id: str):
		# Session
		self.user_id = user_id
		self.session_id = session_id
		self.memory_id = memory_id
		# Config
		self.max_buffer_chars = 500
		self.block_prefix = '{'
		# State
		self.state: StreamState | None = None
		self.buffer: str = ''
		self.parsing_block: bool = False
		self.content_items: list[MemoryContent] = []
		self.current_message: str = ''
		self.sequence_counter: int = 0
		# Tools
		self.tool_name: str | None = None
		self.tool_args: dict[str, Any] | None = None

	# --- State management methods ---

	def set_state(self, new_state: StreamState):
		self.state = new_state

	def clear_state(self):
		self.state = None
		self.buffer = ''
		self.tool_name = None
		self.tool_args = None

	def get_state(self) -> StreamState | None:
		return self.state

	def get_agent_memory(self) -> AgentMemory:
		"""
		Constructs an AgentMemory object from the parsed
		content items in the stream.
		"""
		# First flush any remaining buffer content
		# into the content items
		self._flush_content()
		return AgentMemory(
			session_id=self.session_id,
			user_id=self.user_id,
			memory_id=self.memory_id,
			sender='agent',
			content=self.content_items,
		)

	def set_tool_call(
		self, tool_name: str, tool_args: dict[str, Any]
	):
		self.tool_name = tool_name
		self.tool_args = tool_args

	def _set_sequence_number(self) -> int:
		current = self.sequence_counter
		self.sequence_counter += 1
		return current

	# --- Buffer management methods ---

	def _add_block_content(self, item: NdJsonItem):
		if item.type == NdJsonTypes.IMAGE:
			content_type = MemoryContentTypes.IMAGE
		elif item.type == NdJsonTypes.LINK:
			content_type = MemoryContentTypes.LINK
		else:
			content_type = MemoryContentTypes.TEXT
		self.content_items.append(
			MemoryContent(
				type=content_type,
				payload=item.payload,
			)
		)

	def _add_message_content(self, message: str):
		self.content_items.append(
			MemoryContent(
				type=MemoryContentTypes.TEXT,
				payload=message,
			)
		)

	def _parse_line(
		self,
		line: str,
	) -> NdJsonItem | None:
		try:
			data = json.loads(line)
			return NdJsonItem.model_validate(data)
		except Exception as e:
			add_breadcrumb(
				category='stream_parsing',
				message='Failed to parse line as NDJSON',
				level=BreadcrumbLevel.ERROR,
				data={
					'error': str(e),
					'line': line,
				},
			)
			sentry_sdk.capture_exception(e)
			return None

	def add_delta(self, delta: str) -> StreamParsingResponse:
		"""
		Adds a new delta to the buffer and
		attempts to parse complete lines of NDJSON.
		Returns a list of parsed items and buffer
		content.
		"""
		# If buffer exceeds max chars without newline,
		# clear it and return buffer content
		if len(self.buffer) > self.max_buffer_chars:
			# Add any remaining message content before clearing
			content = self.buffer
			self._add_message_content(content)
			self.buffer = ''
			self.parsing_block = False
			return StreamParsingResponse(
				code=StreamParsingCode.BUFFER,
				block=NdJsonItem(
					type=NdJsonTypes.TEXT,
					payload=content,
					memory_id=self.memory_id,
					sequence_number=self._set_sequence_number(),
				),
			)

		cprint(
			f'current delta: {delta}\n'
			f'Current buffer: {self.buffer}\n'
			f'Current message: {self.current_message}',
			style=LogStyle.DEFAULT,
		)

		# If block prefix detected move to
		# parsing
		if (self.block_prefix in delta.strip()) or self.parsing_block:
			# Set flag to pause further buffering until
			# block is processed
			self.parsing_block = True
			# Append data to buffer
			self.buffer += delta
			# Split buffer by newline to check for
			# complete lines
			cprint(
				f'Buffering block content on {delta}, \n'
				f'current buffer: {self.buffer}\n'
				f'current message: {self.current_message}',
				style=LogStyle.WARNING,
			)
			if '\n' in self.buffer:
				# Add previous message content if exists
				cprint(
					f'Newline detected in buffer, attempting to '
					f'parse block.\n'
					f'Current buffer: {self.buffer}\n'
					f'Current message: {self.current_message}',
					style=LogStyle.WARNING,
				)
				if self.current_message:
					self._add_message_content(self.current_message)
					self.current_message = ''

				# Attempt to parse block content as NDJSON
				block, self.buffer = self.buffer.split('\n', 1)
				item = self._parse_line(block)
				if item:
					cprint(
						f'Parsed block item: {item}\n'
						f'Remaining buffer: {self.buffer}\n'
						f'Current message: {self.current_message}',
						style=LogStyle.SUCCESS,
					)
					self._add_block_content(item)
					self.parsing_block = False
					return StreamParsingResponse(
						code=StreamParsingCode.BLOCK,
						block=item,
					)
				else:
					# If parsing fails, clear buffer and
					# reset state
					cprint(
						f'Failed to parse block content, \n'
						f'clearing buffer.\n'
						f'Current buffer: {self.buffer}\n'
						f'Current message: {self.current_message}',
						style=LogStyle.ERROR,
					)
					self.buffer = ''
					self.parsing_block = False
					return StreamParsingResponse(
						code=StreamParsingCode.EMPTY,
						block=None,
					)
			else:
				# Continue buffering until newline is
				# detected or max buffer size is exceeded
				return StreamParsingResponse(
					code=StreamParsingCode.EMPTY,
					block=None,
				)

		# If no block prefix and not currently parsing, just
		# return the delta as passthrough
		self.current_message += delta
		return StreamParsingResponse(
			code=StreamParsingCode.PASSTHROUGH,
			block=NdJsonItem(
				type=NdJsonTypes.TEXT,
				payload=delta,
				memory_id=self.memory_id,
				sequence_number=self._set_sequence_number(),
			),
		)

	def flush_buffer(self) -> StreamParsingResponse | None:
		"""
		Flushes any remaining buffer content to assure
		that all content is processed, and returns any
		final content as needed.
		"""
		remainder = self.buffer.strip()
		if remainder:
			self._add_message_content(remainder)
			self.buffer = ''
			return StreamParsingResponse(
				code=StreamParsingCode.BUFFER,
				block=NdJsonItem(
					type=NdJsonTypes.TEXT,
					payload=remainder,
					memory_id=self.memory_id,
					sequence_number=self._set_sequence_number(),
				),
			)
		return None

	def _flush_content(self) -> None:
		"""
		Flushes any remaining buffer content into the
		agent memory and returns the constructed
		AgentMemory object.
		"""
		remainder = self.buffer.strip() + self.current_message.strip()
		if remainder:
			self._add_message_content(remainder)
			self.buffer = ''
			self.current_message = ''
