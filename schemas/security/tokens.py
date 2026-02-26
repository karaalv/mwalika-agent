"""
This module defines schemas related to tokens
in the Mwalika Agent system, specifically for
security and tracking purposes. These schemas
are used to enforce security policies related to
token usage.
"""

from enum import Enum

from pydantic import BaseModel, Field


class TokenType(str, Enum):
	"""
	Enumeration of possible token types in the Mwalika Agent system,
	such as access tokens, refresh tokens, or other relevant types
	that can be used for authentication and authorization purposes.
	"""

	ACCESS = 'access'
	REFRESH = 'refresh'


class BaseTokenUsageStats(BaseModel):
	"""
	Represents usage statistics for a refresh token in the
	Mwalika Agent system, which can be used for
	monitoring, analytics, and enforcing rate limits.
	"""

	token_type: TokenType = Field(
		...,
		description=(
			'The type of the token for which these usage stats are '
			'being tracked.'
		),
	)
	token_jti: str = Field(
		...,
		description=(
			'The JTI (JWT ID) of the token for which these usage '
			'stats are being tracked.'
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
			'The number of times the token has been blocked, '
			'which can be useful for monitoring repeat offenders '
			'and enforcing escalating consequences for repeated '
			'violations of security policies'
		),
	)
	last_blocked_at: int | None = Field(
		default=None,
		description=(
			"The timestamp of the token's last block, which can be "
			'useful for tracking block durations and managing data '
			'retention policies'
		),
	)
	requests_today: int = Field(
		default=0,
		description=(
			'The number of API requests made by the token today, '
			'which can be used to enforce daily rate limits'
		),
	)
	last_api_request_at: int | None = Field(
		default=None,
		description=(
			"The timestamp of the token's last API request, "
			'which can be used to enforce rate limits based on '
			'time intervals'
		),
	)


class RefreshTokenUsageStats(BaseTokenUsageStats):
	"""
	Represents usage statistics specifically for refresh tokens in the
	Mwalika Agent system, which can be used for monitoring, analytics,
	and enforcing rate limits related to token generation and usage.
	"""

	access_tokens_generated_today: int = Field(
		default=0,
		description=(
			'The number of access tokens generated using this '
			'refresh token today.'
		),
	)


class AccessTokenUsageStats(BaseTokenUsageStats):
	"""
	Represents usage statistics specifically for access tokens in the
	Mwalika Agent system, which can be used for monitoring, analytics,
	and enforcing rate limits related to API access and interactions.
	"""

	bad_requests_today: int = Field(
		default=0,
		description=(
			'The number of bad requests (e.g., malformed, missing '
			'parameters) made by the token today, which can be used '
			'to identify potential abuse or issues with client '
			'implementations'
		),
	)
	agent_input_tokens_today: int = Field(
		default=0,
		description=(
			'The total number of input tokens sent to agents by '
			'the token today, which can be used to enforce '
			'token-based rate limits'
		),
	)
	claim_cookies_generated_today: int = Field(
		default=0,
		description=(
			'The number of times this access token has been used to '
			'claim a user cookie today.'
		),
	)
