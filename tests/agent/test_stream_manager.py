"""
This module contains tests for the StreamManager
class, which is responsible for managing the state
and processing of events from the OpenAI API response
into the desired format.
"""

from agent.streaming.stream_manager import StreamManager
from schemas.agent.memory import (
	MemoryContentTypes,
)
from schemas.agent.stream import (
	NdJsonTypes,
	StreamParsingCode,
)
from shared.ids import generate_uuid_str

# --- Test utils ---


def _make_sm() -> StreamManager:
	return StreamManager(
		user_id=generate_uuid_str(),
		session_id=generate_uuid_str(),
		memory_id=generate_uuid_str(),
		verbosity_level=1,
	)


# --- Tests for StreamManager ---


def test_passthrough_delta():
	manager = _make_sm()

	response = manager.add_delta('hello')
	assert response.code == StreamParsingCode.PASSTHROUGH
	assert response.block is not None
	assert response.block.type == NdJsonTypes.TEXT
	assert response.block.payload == 'hello'

	response = manager.add_delta(' world')
	assert response.code == StreamParsingCode.PASSTHROUGH
	assert response.block is not None
	assert response.block.type == NdJsonTypes.TEXT
	assert response.block.payload == ' world'

	memory = manager.get_agent_memory()
	text_payloads = [item.payload for item in memory.content]
	assert ''.join(text_payloads) == 'hello world'


def test_ndjson_block_single_chunk():
	sm = _make_sm()

	line = '{"type":"link","payload":"https://x"}\n'

	resp = sm.add_delta(line)

	assert resp.code == StreamParsingCode.BLOCK
	assert resp.block is not None
	assert resp.block.type == NdJsonTypes.LINK
	assert resp.block.payload == 'https://x'

	mem = sm.get_agent_memory()
	assert len(mem.content) == 1
	assert mem.content[0].payload == 'https://x'


def test_ndjson_block_split_across_chunks():
	sm = _make_sm()

	part1 = '{"type":"image","payload":"https://i'
	part2 = 'mg"}\n'

	resp1 = sm.add_delta(part1)
	assert resp1.code == StreamParsingCode.EMPTY
	assert resp1.block is None

	resp2 = sm.add_delta(part2)
	assert resp2.code == StreamParsingCode.BLOCK
	assert resp2.block is not None
	assert resp2.block.type == NdJsonTypes.IMAGE
	assert resp2.block.payload == 'https://img'

	mem = sm.get_agent_memory()
	assert len(mem.content) == 1
	assert mem.content[0].type == MemoryContentTypes.IMAGE
	assert mem.content[0].payload == 'https://img'


def test_block_flushes_prior_text():
	sm = _make_sm()

	resp1 = sm.add_delta('Before block. ')
	assert resp1.code == StreamParsingCode.PASSTHROUGH

	line = '{"type":"link","payload":"https://x"}\n'
	resp2 = sm.add_delta(line)

	assert resp2.code == StreamParsingCode.BLOCK

	mem = sm.get_agent_memory()
	assert len(mem.content) == 2

	assert mem.content[0].type == MemoryContentTypes.TEXT
	assert mem.content[0].payload == 'Before block. '

	assert mem.content[1].type == MemoryContentTypes.LINK
	assert mem.content[1].payload == 'https://x'


def test_invalid_ndjson_clears_buffer_and_returns_empty():
	sm = _make_sm()

	bad = '{"type":"link","payload":"oops"\n'
	resp = sm.add_delta(bad)

	assert resp.code == StreamParsingCode.EMPTY
	assert resp.block is None

	assert sm.buffer == ''
	assert sm.parsing_block is False


def test_buffer_overflow_emits_buffer_code_and_resets():
	sm = _make_sm()
	sm.max_buffer_chars = 10

	# Force buffer to exceed max before call
	sm.buffer = 'x' * 11
	sm.parsing_block = True

	resp = sm.add_delta('ignored')

	assert resp.code == StreamParsingCode.BUFFER
	assert resp.block is not None
	assert resp.block.type == NdJsonTypes.TEXT
	assert resp.block.payload == 'x' * 11

	assert sm.buffer == ''
	assert sm.parsing_block is False
