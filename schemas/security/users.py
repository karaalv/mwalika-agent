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
	day_key: str = Field(
		...,
		description=(
			'A string representing the current day ("2024-06-01") '
			'used to reset daily stats and enforce daily limits'
		),
	)
	blocked_count: int = Field(
		default=0,
		description=(
			'The number of times the user has been blocked, '
			'which can be useful for monitoring repeat offenders '
			'and enforcing escalating consequences for repeated '
			'violations of security policies'
		),
	)
	last_blocked_at: int | None = Field(
		default=None,
		description=(
			"The timestamp of the user's last block, which can be "
			'useful for tracking block durations and managing data '
			'retention policies'
		),
	)
	requests_today: int = Field(
		default=0,
		description=(
			'The number of API requests made by the user today, '
			'which can be used to enforce daily rate limits'
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
	active_ws_connections: list[str] = Field(
		default_factory=list,
		description=(
			'A list of active WebSocket connection IDs associated '
			'with the user, which can be used to manage real-time '
			'interactions and enforce limits on concurrent '
			'connections'
		),
	)
	bad_requests_today: int = Field(
		default=0,
		description=(
			'The number of bad requests (e.g., malformed, missing '
			'parameters) made by the user today, which can be used '
			'to identify potential abuse or issues with client '
			'implementations'
		),
	)
	last_api_request_at: int | None = Field(
		default=None,
		description=(
			"The timestamp of the user's last API request, "
			'which can be used to enforce rate limits based on '
			'time intervals'
		),
	)
	access_tokens_generated_today: int = Field(
		default=0,
		description=(
			'The number of access tokens generated using this '
			'refresh token today.'
		),
	)
	claim_cookies_generated_today: int = Field(
		default=0,
		description=(
			'The number of times this access token has been used to '
			'claim a user cookie today.'
		),
	)
