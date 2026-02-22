"""
This module contains schemas related to user
management and security within the Mwalika Agent system,
including usage statistics, rate limiting, and other security-related
data structures.
"""

from pydantic import BaseModel, Field


class UserUsageStats(BaseModel):
	"""
	Represents usage statistics for a user in the
	Mwalika Agent system, which can be used for
	monitoring, analytics, and enforcing rate limits.
	"""

	user_id: str = Field(
		...,
		description=(
			'The unique identifier of the user for whom '
			'these usage stats are being tracked'
		),
	)
	requests_today: int = Field(
		default=0,
		description=(
			'The number of API requests made by the user today, '
			'which can be used to enforce daily rate limits'
		),
	)
	agent_input_tokens: int = Field(
		default=0,
		description=(
			'The total number of input tokens sent to agents by '
			'the user, which can be used to enforce token-based '
			'rate limits'
		),
	)
	agent_input_tokens_today: int = Field(
		default=0,
		description=(
			'The total number of input tokens sent to agents by '
			'the user today, which can be used to enforce '
			'token-based rate limits'
		),
	)
	last_request_timestamp: str = Field(
		default='',
		description=(
			"The timestamp of the user's last API request, "
			'which can be used to enforce rate limits based on '
			'time intervals'
		),
	)
