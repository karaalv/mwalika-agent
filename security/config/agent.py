"""
This module defines configuration settings for
security-related components of the Mwalika Agent, such as
content sizes and other parameters that can be used across the
application to maintain consistent security policies and limits.
"""

MAX_CONTENT_SIZE_BYTES = 16 * 1024  # 16 KB
MAX_INPUT_LENGTH = 2_000  # Maximum number of characters for input
MAX_SINGLE_INPUT_TOKEN_LENGTH = 100
