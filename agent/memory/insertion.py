"""
This module contains logic for creating and
inserting new memory entries into the agent's
memory storage, which is used to store interactions
and context for agent sessions.
"""

from typing import Literal

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.agent.memory import (
	AgentMemory,
	MemoryContent,
	MemoryContentTypes,
)


async def insert_agent_memory(
	memory_entry: AgentMemory,
) -> AgentMemory:
	"""
	Inserts a new memory entry into the MongoDB collection
	for the given session and user.
	"""
	memory_collection = await get_collection(
		MongoDBCollection.MEMORIES
	)
	await memory_collection.insert_one(
		memory_entry.model_dump(mode='json')
	)
	return memory_entry


async def insert_agent_memory_content(
	session_id: str,
	user_id: str,
	sender: Literal['user', 'agent'],
	content: list[MemoryContent],
) -> AgentMemory:
	"""
	Creates a new memory entry and inserts it into
	the MongoDB collection for the given session and
	user.
	"""
	memory_entry = AgentMemory(
		session_id=session_id,
		user_id=user_id,
		sender=sender,
		content=content,
	)
	memory_collection = await get_collection(
		MongoDBCollection.MEMORIES
	)
	await memory_collection.insert_one(
		memory_entry.model_dump(mode='json')
	)
	return memory_entry


async def insert_user_input_memory(
	session_id: str,
	user_id: str,
	user_input: str,
) -> AgentMemory:
	"""
	Creates a new memory entry for user input and
	inserts it into the MongoDB collection.
	"""
	content = [
		MemoryContent(
			type=MemoryContentTypes.TEXT,
			payload=user_input,
		)
	]
	return await insert_agent_memory_content(
		session_id=session_id,
		user_id=user_id,
		sender='user',
		content=content,
	)
