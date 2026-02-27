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
	StreamItem,
	StreamParsingCode,
	StreamParsingResponse,
	StreamState,
)
from shared.logging import LogStyle, cprint


class StreamManager:
	"""
	Manages the state of the OpenAI response stream,
	including buffering and processing of events.
	"""

	def __init__(
		self,
		user_id: str,
		session_id: str,
		memory_id: str,
		verbosity_level: int = 0,
	):
		# Session
		self.user_id = user_id
		self.session_id = session_id
		self.memory_id = memory_id
		# Config
		self.verbosity_level = verbosity_level
		self.max_buffer_chars = 500
		self.block_start = '{'
		self.block_end = '\n'
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
		self.parsing_block = False
		self.content_items = []
		self.current_message = ''
		self.sequence_counter = 0
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

	def _add_block_content(self, item: StreamItem):
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
	) -> StreamItem | None:
		try:
			data = json.loads(line)
			ndjson = NdJsonItem.model_validate(data)
			return StreamItem(
				type=ndjson.type,
				payload=ndjson.payload,
				memory_id=self.memory_id,
				sequence_number=self._set_sequence_number(),
			)
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
			if self.verbosity_level > 0:
				cprint(
					f'Error parsing line as NDJSON: {e}'
					f'\nLine content: {line}',
					style=LogStyle.ERROR,
				)

	def add_delta(self, delta: str) -> StreamParsingResponse:
		"""
		Adds a new delta to the buffer and
		attempts to parse complete lines of NDJSON.
		Returns a list of parsed items and buffer
		content.
		"""
		# Used to track if buffer content has
		# already been added from current delta
		buffer_seeded = False

		# A. If buffer exceeds max chars without newline,
		# clear it and return buffer content
		if len(self.buffer) > self.max_buffer_chars:
			# Add any remaining message content before clearing
			content = self.buffer
			self._add_message_content(content)
			self.buffer = ''
			self.parsing_block = False
			return StreamParsingResponse(
				code=StreamParsingCode.BUFFER,
				block=StreamItem(
					type=NdJsonTypes.TEXT,
					payload=content,
					memory_id=self.memory_id,
					sequence_number=self._set_sequence_number(),
				),
			)

		if self.verbosity_level > 0:
			cprint(
				f'current delta: {delta}\n'
				f'Current buffer: {self.buffer}\n'
				f'Current message: {self.current_message}',
				style=LogStyle.DEFAULT,
			)

		# B. Check for block prefix to start buffering
		# and parsing block content
		if self.block_start in delta and not self.parsing_block:
			# Split delta by prefix, add prefix to
			# buffer
			pre_prefix, post_prefix = delta.split(self.block_start, 1)
			self.buffer = self.block_start + post_prefix
			buffer_seeded = True

			# Set flag to start parsing block content
			self.parsing_block = True

			# If there is any content before the block prefix,
			# add it to the current message and return
			# as passthrough
			if pre_prefix:
				# Add pre-prefix content to current message
				# adn save content to memory items
				self.current_message += pre_prefix
				self._add_message_content(pre_prefix)
				self.current_message = ''
				return StreamParsingResponse(
					code=StreamParsingCode.PASSTHROUGH,
					block=StreamItem(
						type=NdJsonTypes.TEXT,
						payload=pre_prefix,
						memory_id=self.memory_id,
						sequence_number=self._set_sequence_number(),
					),
				)
			else:
				# Save current message content before moving
				# to parsing block content
				if self.current_message:
					self._add_message_content(self.current_message)
					self.current_message = ''

		# C. If currently parsing a block, continue buffering
		# until newline is detected to parse block content
		# or max buffer size is exceeded
		if self.parsing_block:
			if not buffer_seeded:
				self.buffer += delta
				buffer_seeded = True

			if self.block_end in self.buffer:
				# Attempt to parse block content as NDJSON
				block, remainder = self.buffer.split(
					self.block_end, 1
				)
				item = self._parse_line(block)
				self.buffer = ''
				self.parsing_block = False

				# Add any remaining content to the
				# current message to be included in
				# memory items
				if remainder:
					self.current_message += remainder

				if item:
					self._add_block_content(item)
					return StreamParsingResponse(
						code=StreamParsingCode.BLOCK,
						block=item,
					)
				else:
					# If parsing fails reset state and
					# drop buffer content
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

		# D. If no block prefix and not currently parsing, just
		# return the delta as passthrough
		self.current_message += delta
		return StreamParsingResponse(
			code=StreamParsingCode.PASSTHROUGH,
			block=StreamItem(
				type=NdJsonTypes.TEXT,
				payload=delta,
				memory_id=self.memory_id,
				sequence_number=self._set_sequence_number(),
			),
		)

	def flush_manager(self) -> StreamParsingResponse:
		"""
		Flushes any remaining buffer content to assure
		that all content is processed, and returns any
		final content as needed.
		"""
		remainder = self.buffer.strip() + self.current_message.strip()
		if remainder:
			self._add_message_content(remainder)
			self.buffer = ''
			self.current_message = ''
			return StreamParsingResponse(
				code=StreamParsingCode.BUFFER,
				block=StreamItem(
					type=NdJsonTypes.TEXT,
					payload=remainder,
					memory_id=self.memory_id,
					sequence_number=self._set_sequence_number(),
				),
			)
		else:
			return StreamParsingResponse(
				code=StreamParsingCode.EMPTY,
				block=None,
			)

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
