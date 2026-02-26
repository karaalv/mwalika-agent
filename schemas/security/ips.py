"""
This module defines schemas related to IP address
management and security in the Mwalika Agent system, including
schemas for tracking IP usage statistics, blocked IP addresses,
and other relevant data structures that can be used for monitoring,
analytics, and enforcing security policies related to IP addresses.
"""

from pydantic import BaseModel, Field


class IPUsageStats(BaseModel):
	"""
	Represents usage statistics for an IP address in the
	Mwalika Agent system, which can be used for
	monitoring, analytics, and enforcing rate limits.
	"""

	ip_address: str = Field(
		...,
		description=(
			'The IP address for which these usage '
			'stats are being tracked'
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
			'The number of times the IP address has been blocked, '
			'which can be useful for monitoring repeat offenders '
			'and enforcing escalating consequences for repeated '
			'violations of security policies'
		),
	)
	last_blocked_at: int | None = Field(
		default=None,
		description=("The timestamp of the IP address's last block"),
	)
	requests_today: int = Field(
		default=0,
		description=(
			'The number of API requests made by the IP address today.'
		),
	)
	agent_input_tokens_today: int = Field(
		default=0,
		description=(
			'The total number of input tokens sent to agents by '
			'the IP address today, which can be used to enforce '
			'token-based rate limits'
		),
	)
	active_ws_connections: list[str] = Field(
		default_factory=list,
		description=(
			'A list of active WebSocket connection IDs associated '
			'with the IP address. '
		),
	)
	bad_requests_today: int = Field(
		default=0,
		description=(
			'The number of bad requests (e.g., malformed, missing '
			'parameters) made by the IP address today.'
		),
	)
	last_api_request_at: int | None = Field(
		default=None,
		description=(
			"The timestamp of the IP address's last API request."
		),
	)
	refresh_tokens_generated_today: int = Field(
		default=0,
		description=(
			'The number of refresh tokens generated using this IP '
			'address, which can be used to enforce limits on token '
			'generation and monitor for potential abuse related to '
			'token creation from specific IP addresses over time '
			'intervals'
		),
	)
	claim_cookies_generated_today: int = Field(
		default=0,
		description=(
			'The number of times this access token has been used to '
			'claim a user cookie today.'
		),
	)
