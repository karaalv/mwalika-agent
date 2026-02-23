"""
This module defines specific rate limiting policies
for the Mwalika Agent, these policies can be applied to API routes
to control the rate of incoming requests across different
resource types.
"""

from schemas.security.ratelimit import (
	PolicyConfig,
	ResourcePolicyType,
)

# --- Policy mapping ---

POLICY_LIMITER_CONFIG_MAPPING: dict[
	ResourcePolicyType, dict[str, PolicyConfig]
] = {
	ResourcePolicyType.SYSTEM: {
		'ip': PolicyConfig(max_rate=500, time_period=60),
		'user': PolicyConfig(max_rate=100, time_period=60),
	},
	ResourcePolicyType.REFRESH_TOKEN: {
		'ip': PolicyConfig(max_rate=300, time_period=60),
		'user': PolicyConfig(max_rate=10, time_period=60),
	},
	ResourcePolicyType.ACCESS_TOKEN: {
		'ip': PolicyConfig(max_rate=300, time_period=60),
		'user': PolicyConfig(max_rate=20, time_period=60),
	},
	ResourcePolicyType.CLAIM_USER_COOKIE: {
		'ip': PolicyConfig(max_rate=300, time_period=60),
		'user': PolicyConfig(max_rate=5, time_period=60),
	},
	ResourcePolicyType.AGENT_INTERACTION: {
		'ip': PolicyConfig(max_rate=300, time_period=60),
		'user': PolicyConfig(max_rate=60, time_period=60),
	},
	ResourcePolicyType.AGENT_MESSAGING: {
		'ip': PolicyConfig(max_rate=500, time_period=60),
		'user': PolicyConfig(max_rate=20, time_period=60),
	},
}
