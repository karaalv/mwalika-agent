"""
This module defines prompts related to managing
control flow for tool usage in the agent.
"""

from textwrap import dedent


def return_successful_tool_response(
	tool_name: str, tool_response: str
) -> str:
	"""
	Formats a successful tool response
	for the agent to use.
	"""
	return dedent(
		f"""
        The tool "{tool_name}" succeeded.

        Use the provided data to answer the user.

        Do not mention internal processing.

        Data:
        {tool_response}
        """
	).strip()


def return_failed_tool_response(tool_name: str) -> str:
	"""
	Formats a failed tool response
	for the agent to use.
	"""
	return dedent(
		f"""
        The tool "{tool_name}" did not
        provide usable data.

        Do not mention internal failure.

        Either:
        - ask a clarifying question, or
        - state insufficient information.

        Remain focused on government services.
        """
	).strip()
