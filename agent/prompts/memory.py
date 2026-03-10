"""
This module defines prompting utilities related
to memory management for the Mwalika Agent, such as
functions to retrieve and format memory entries for use in
agent prompts.
"""

from collections.abc import Iterable
from textwrap import dedent

from schemas.agent.memory import AgentMemory, MemoryContentTypes

_DEFAULT_MEMORY_PROMPT_LIMIT = 30


def format_agent_memory_prompt(
	memories: Iterable[AgentMemory],
	limit: int = _DEFAULT_MEMORY_PROMPT_LIMIT,
) -> str:
	"""
	Formats the latest agent memory entries into a
	compact chronological transcript suitable for
	LLM prompting.

	Args:
		memories:
			Iterable of AgentMemory entries.
		limit:
			Maximum number of latest memory entries to
			include in the prompt.

	Returns:
			A formatted prompt string.
	"""

	sorted_memories = sorted(
		memories,
		key=lambda memory: memory.timestamp,
	)

	if limit > 0:
		sorted_memories = sorted_memories[-limit:]

	lines: list[str] = []

	for memory in sorted_memories:
		role = memory.sender.upper()
		timestamp = memory.timestamp

		for item in memory.content:
			if item.type == MemoryContentTypes.TEXT:
				lines.append(f'[{timestamp}] {role}: {item.payload}')

			elif item.type == MemoryContentTypes.IMAGE:
				lines.append(
					f'[{timestamp}] {role}: [image] {item.payload}'
				)

			elif item.type == MemoryContentTypes.LINK:
				lines.append(
					f'[{timestamp}] {role}: [link] {item.payload}'
				)

	transcript = '\n'.join(lines).strip()

	if not transcript:
		transcript = '[No prior conversation history]'

	return dedent(
		f"""
		The following is the conversation history
		for the current session.

		Conversation history:
		{transcript}

		Continue the conversation naturally and
		consistently with the prior context.
		""".strip()
	)
