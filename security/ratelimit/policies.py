"""
This module defines specific rate limiting policies
for the Mwalika Agent, these policies can be applied to API routes
to control the rate of incoming requests across different
resource types.
"""

from schemas.security.ratelimit import (
	PolicyConfig,
	ResourcePolicyIdentifierType,
	ResourcePolicyType,
)

# --- Policy mapping ---

POLICY_LIMITER_CONFIG_MAPPING: dict[
	ResourcePolicyType,
	dict[ResourcePolicyIdentifierType, PolicyConfig],
] = {
	ResourcePolicyType.SYSTEM: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=500, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=100, time_period=60
		),
	},
	ResourcePolicyType.API_DEPENDENCY: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=500, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=30, time_period=60
		),
	},
	ResourcePolicyType.REFRESH_TOKEN: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=100, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=5, time_period=60
		),
	},
	ResourcePolicyType.ACCESS_TOKEN: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=100, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=20, time_period=60
		),
	},
	ResourcePolicyType.CLAIM_USER_COOKIE: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=100, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=5, time_period=60
		),
	},
	ResourcePolicyType.AGENT_INTERACTION: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=300, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=10, time_period=60
		),
	},
	ResourcePolicyType.AGENT_MESSAGING: {
		ResourcePolicyIdentifierType.IP: PolicyConfig(
			max_rate=500, time_period=60
		),
		ResourcePolicyIdentifierType.USER: PolicyConfig(
			max_rate=20, time_period=60
		),
	},
}
