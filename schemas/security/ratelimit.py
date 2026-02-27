"""
This module defines schemas related to rate limiting for
the Mwalika Agent system, including the structure for storing
rate limiter instances in memory and any related data models
that are used for managing and enforcing rate limits across
different API routes and resource types.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from aiolimiter import AsyncLimiter

from shared.time import get_timestamp_s

# --- Resource policy types ---


class ResourcePolicyType(str, Enum):
	"""
	Defines the types of resource policies that can be applied
	to API routes for rate limiting purposes.
	"""

	SYSTEM = 'system'
	API_DEPENDENCY = 'api_dependency'
	REFRESH_TOKEN = 'refresh_token'
	ACCESS_TOKEN = 'access_token'
	CLAIM_USER_COOKIE = 'claim_user_cookie'
	AGENT_INTERACTION = 'agent_interaction'
	AGENT_MESSAGING = 'agent_messaging'


# --- Policy configuration dataclass ---


@dataclass(slots=True)
class PolicyConfig:
	"""
	Represents the configuration for a specific rate limiting policy,
	including the maximum number of requests allowed and the time
	period for the limit.
	"""

	max_rate: int
	time_period: int


# --- Rate limiter schema ---


@dataclass(slots=True)
class RateLimiter:
	"""
	Represents a rate limiter instance for a specific resource
	policy and identifier (e.g., IP or user ID). This schema is
	used to store and manage limiter instances in memory.
	"""

	policy_type: ResourcePolicyType
	identifier_type: Literal['ip', 'user']
	identifier_value: str
	limiter: AsyncLimiter
	created_at: int = field(default_factory=get_timestamp_s)
