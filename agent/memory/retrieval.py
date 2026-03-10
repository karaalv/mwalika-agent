"""
This module contains logic for retrieving
relevant memory entries from the agent's
memory storage based on the current session and
context.
"""

from agent.prompts.memory import format_agent_memory_prompt
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
	memory_collection = get_collection(MongoDBCollection.MEMORIES)
	memory_entries = await memory_collection.find(
		{
			'session_id': session_id,
			'user_id': user_id,
		},
		sort=[('timestamp', 1)],
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
	memories = await retrieve_agent_memory(session_id, user_id)
	return format_agent_memory_prompt(memories)
