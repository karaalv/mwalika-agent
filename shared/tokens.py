"""
This module contains shared utilities for managing
tokens across the Mwalika Agent system.
"""

import tiktoken

# --- Tokenizer instance ---

_tokenizer = tiktoken.get_encoding('gpt-4o')

# --- Token counting utility function ---


def count_tokens(text: str) -> int:
	"""
	Counts the number of tokens in a given text string
	using the tiktoken library, which is compatible with
	OpenAI's tokenization.
	"""
	return len(_tokenizer.encode(text))
