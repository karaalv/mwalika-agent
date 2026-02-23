"""
This module provides a centralized store for rate limiters,
allowing for easy access and management of different rate limiting
policies across the Mwalika Agent.
"""

from typing import Literal

from aiolimiter import AsyncLimiter

from schemas.security.ratelimit import RateLimiter
from security.ratelimit.policies import (
	POLICY_LIMITER_CONFIG_MAPPING,
	ResourcePolicyType,
)

# --- User route limiters ---

_limiters: dict[str, RateLimiter] = {}

# --- Accessor function for limiters ---


def get_limiter(
	policy_type: ResourcePolicyType,
	identifier_type: Literal['ip', 'user'],
	identifier_value: str,
) -> AsyncLimiter:
	"""
	Retrieves the appropriate AsyncLimiter instance based on the
	specified policy type and identifier type (e.g., 'ip' or 'user').
	This function allows API routes to easily access the correct
	limiter for enforcing rate limits.
	"""
	key = f'{policy_type.value}:{identifier_type}:{identifier_value}'
	if key not in _limiters:
		config = POLICY_LIMITER_CONFIG_MAPPING[policy_type][
			identifier_type
		]
		limiter = RateLimiter(
			policy_type=policy_type,
			identifier_type=identifier_type,
			identifier_value=identifier_value,
			limiter=AsyncLimiter(config.max_rate, config.time_period),
		)
		_limiters[key] = limiter
	return _limiters[key].limiter
