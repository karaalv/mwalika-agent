"""
This module defines the configuration settings for
observers that monitor user, token and IP usage
statistics and enforce security policies in the Mwalika Agent
system. These settings include limits on daily requests, token usage,
and block durations based on severity levels, which can be used
across the application to maintain consistent security policies and
enforcement mechanisms.
"""


# --- User usage limits ---

MAX_DAILY_AT_GENERATED_PER_USER = 200
MAX_DAILY_CLAIM_COOKIES_PER_USER = 5

MAX_PER_MINUTE_REQUESTS_PER_USER = 30
MAX_DAILY_REQUESTS_PER_USER = 300
MAX_DAILY_BAD_REQUESTS_PER_USER = 20
MAX_WS_CONNECTIONS_PER_USER = 5
MAX_AGENT_SESSIONS_PER_USER = 3

MAX_DAILY_AGENT_INPUT_TOKENS_PER_USER = 50_000

# --- IP usage limits ---

MAX_DAILY_REFRESH_TOKENS_PER_IP = 300
MAX_DAILY_CLAIM_COOKIES_PER_IP = 300

MAX_PER_MINUTE_REQUESTS_PER_IP = 500
MAX_DAILY_REQUESTS_PER_IP = 10_000
MAX_DAILY_BAD_REQUESTS_PER_IP = 500
MAX_WS_CONNECTIONS_PER_IP = 100

MAX_DAILY_AGENT_INPUT_TOKENS_PER_IP = 1_000_000

# --- Token usage limits ---

# Refresh token

MAX_PER_MINUTE_REQUESTS_PER_RT = 10
# Note this covers general usage and AT generation,
# which is the main source of usage for RTs,
# so we can use the same limit for both
MAX_DAILY_REQUESTS_PER_RT = 200

# Access token

MAX_PER_MINUTE_REQUESTS_PER_AT = 20
MAX_DAILY_REQUESTS_PER_AT = 100
MAX_DAILY_BAD_REQUESTS_PER_AT = 20
MAX_DAILY_CLAIM_COOKIES_GENERATED_PER_AT = 5

MAX_DAILY_AGENT_INPUT_TOKENS_PER_AT = 5_000

# --- Blocking parameters ---

# General

FORGIVENESS_PERIOD_SECONDS = 60 * 60 * 24 * 3  # 3 days in seconds
HOURS_IN_SECONDS_24 = 24 * 60 * 60

# User block durations based on severity levels
USER_BLOCK_DURATION_LV_1 = 1 * 60 * 60  # 1 hour in seconds
USER_BLOCK_DURATION_LV_2 = 24 * 60 * 60  # 24 hours in seconds
USER_BLOCK_DURATION_LV_3 = 7 * 24 * 60 * 60  # 7 days in seconds

# WebSocket block durations based on severity levels
WS_BLOCK_DURATION_LV_1 = 60 * 15  # 15 minutes in seconds
WS_BLOCK_DURATION_LV_2 = 60 * 60  # 1 hour in seconds
WS_BLOCK_DURATION_LV_3 = 60 * 60 * 24  # 24 hours in seconds

# Agent input token block durations based on severity levels
AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1 = (
	24 * 60 * 60
)  # 24 hours in seconds
AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2 = (
	48 * 60 * 60
)  # 2 days in seconds
AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3 = (
	7 * 24 * 60 * 60
)  # 7 days in seconds

# Refresh token block durations based on severity levels
REFRESH_TOKEN_BLOCK_DURATION_LV_1 = 1 * 60 * 60  # 1 hour in seconds
REFRESH_TOKEN_BLOCK_DURATION_LV_2 = (
	24 * 60 * 60
)  # 24 hours in seconds
REFRESH_TOKEN_BLOCK_DURATION_LV_3 = (
	7 * 24 * 60 * 60
)  # 7 days in seconds

# IP block durations based on severity levels
IP_BLOCK_DURATION_LV_1 = 1 * 60 * 60  # 1 hour in seconds
IP_BLOCK_DURATION_LV_2 = 24 * 60 * 60  # 24 hours in seconds
IP_BLOCK_DURATION_LV_3 = 7 * 24 * 60 * 60  # 7 days in seconds

# Access token block duration - note it blocks until
# the token expires, so we don't need multiple levels
ACCESS_TOKEN_BLOCK_DURATION = 24 * 60 * 60  # 24 hours in seconds
