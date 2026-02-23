"""
This module defines schemas related to rate limiting for
the Mwalika Agent system, including the structure for storing
rate limiter instances in memory and any related data models
that are used for managing and enforcing rate limits across
different API routes and resource types.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

from aiolimiter import AsyncLimiter
from pydantic import BaseModel, Field

from shared.time import get_datetime

# --- Resource policy types ---


class ResourcePolicyType(str, Enum):
	"""
	Defines the types of resource policies that can be applied
	to API routes for rate limiting purposes.
	"""

	SYSTEM = 'system'
	REFRESH_TOKEN = 'refresh_token'
	ACCESS_TOKEN = 'access_token'
	CLAIM_USER_COOKIE = 'claim_user_cookie'
	AGENT_INTERACTION = 'agent_interaction'
	AGENT_MESSAGING = 'agent_messaging'


# --- Policy configuration dataclass ---


@dataclass
class PolicyConfig:
	"""
	Represents the configuration for a specific rate limiting policy,
	including the maximum number of requests allowed and the time
	period for the limit.
	"""

	max_rate: int
	time_period: int


# --- Rate limiter schema ---


class RateLimiter(BaseModel):
	"""
	Represents a rate limiter instance for a specific resource
	policy and identifier (e.g., IP or user ID). This schema is
	used to store and manage limiter instances in memory.
	"""

	policy_type: ResourcePolicyType = Field(
		...,
		description=(
			'The type of resource policy '
			'this limiter is associated with'
		),
	)
	identifier_type: Literal['ip', 'user'] = Field(
		...,
		description=(
			'The type of identifier this limiter is based on, '
			"either 'ip' for IP-based limits or 'user' for "
			'user-based limits'
		),
	)
	identifier_value: str = Field(
		...,
		description=(
			'The specific value of the identifier '
			'(e.g., the IP address '
			'or user ID) that this limiter applies to'
		),
	)
	limiter: AsyncLimiter = Field(
		...,
		description=(
			'The actual AsyncLimiter instance that '
			'enforces the rate limit'
		),
	)
	created_at: datetime = Field(
		default_factory=get_datetime,
		description=(
			'The timestamp when this limiter instance was created, '
			'which can be '
			'used for monitoring and cleanup purposes'
		),
	)
