"""
This module contains logic for retrieving
relevant memory entries from the agent's
memory storage based on the current session and
context.
"""

import json
from textwrap import dedent

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.agent.memory import AgentMemory


async def retrieve_agent_memory(
	session_id: str,
	user_id: str,
) -> list[AgentMemory]:
	"""
	Retrieves relevant memory entries for a given
	agent session and user, ordered by most recent.
	"""
	memory_collection = await get_collection(
		MongoDBCollection.MEMORIES
	)
	memory_entries = await memory_collection.find(
		{
			'session_id': session_id,
			'user_id': user_id,
		},
		sort=[('timestamp', -1)],
	).to_list()
	return [
		AgentMemory.model_validate(entry) for entry in memory_entries
	]


async def retrieve_agent_memory_prompt(
	session_id: str,
	user_id: str,
) -> str:
	"""
	Retrieves relevant memory entries and
	formats them into a prompt for the agent.
	"""
	prompt_start = dedent(
		"""
        Here is the relevant memory from the current session:
        """.strip()
	)
	memories = await retrieve_agent_memory(session_id, user_id)
	memories_dict = [m.model_dump(mode='json') for m in memories]
	return prompt_start + '\n\n' + json.dumps(memories_dict, indent=2)
