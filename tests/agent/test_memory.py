"""
This module contains tests for validating the
functionality of the agent's memory management.
"""

from typing import Literal

from agent.memory.insertion import insert_agent_memory_content
from agent.memory.retrieval import (
	retrieve_agent_memory,
	retrieve_agent_memory_prompt,
)
from databases.mongodb.main import MongoDBCollection
from schemas.agent.memory import (
	AgentMemory,
	MemoryContent,
	MemoryContentTypes,
)
from shared.ids import generate_uuid_str
from tests.utils.mongodb import clear_collection

# --- Utility Functions ---


async def _create_test_memory_entry(
	session_id: str,
	user_id: str,
	sender: Literal['user', 'agent'],
	content: list[MemoryContent],
) -> AgentMemory:
	"""
	Creates a test memory entry for use in
	memory retrieval tests.
	"""
	return await insert_agent_memory_content(
		session_id=session_id,
		user_id=user_id,
		sender=sender,
		content=content,
	)


# --- Test Cases ---


async def test_insert_and_retrieve_agent_memory():
	"""
	Tests the insertion of a memory entry and
	subsequent retrieval to validate that the
	memory management functions are working as
	expected.
	"""
	test_user_id = generate_uuid_str()
	test_session_id = generate_uuid_str()

	# Create a test memory entry
	test_content = [
		MemoryContent(
			type=MemoryContentTypes.TEXT,
			payload='Test message from user',
		)
	]
	inserted_memory = await insert_agent_memory_content(
		session_id=test_session_id,
		user_id=test_user_id,
		sender='user',
		content=test_content,
	)

	# Retrieve memory entries for the session and user
	retrieved_memories = await retrieve_agent_memory(
		session_id=test_session_id,
		user_id=test_user_id,
	)

	# Validate that the inserted memory is in the retrieved memories
	assert any(
		m.memory_id == inserted_memory.memory_id
		for m in retrieved_memories
	)

	# Test the memory prompt retrieval
	memory_prompt = await retrieve_agent_memory_prompt(
		session_id=test_session_id,
		user_id=test_user_id,
	)
	assert 'Test message from user' in memory_prompt

	# Clean up test data
	await clear_collection(MongoDBCollection.MEMORIES)
