"""
This module defines shared data utilities used
across the Mwalika Agent application, specifically
for working with bytes data, such as encoding and decoding
functions.
"""

import json
from typing import Any

from pydantic import BaseModel


def get_bytes(data: Any) -> int:
	"""
	Return the UTF-8 byte size of the given data.

	Supports:
	- bytes
	- str
	- dict / list
	- numbers
	- Pydantic BaseModel
	- fallback to str(...)
	"""

	if data is None:
		return 0

	# Already bytes
	if isinstance(data, bytes):
		return len(data)

	# String
	if isinstance(data, str):
		return len(data.encode('utf-8'))

	# Pydantic model (v1 + v2 compatible)
	if isinstance(data, BaseModel):
		try:
			# v2
			payload = data.model_dump()
		except AttributeError:
			# v1
			payload = data.dict()

		serialized = json.dumps(
			payload,
			separators=(',', ':'),
			ensure_ascii=False,
		)
		return len(serialized.encode('utf-8'))

	# Dict or list
	if isinstance(data, (dict, list)):
		serialized = json.dumps(
			data,
			separators=(',', ':'),
			ensure_ascii=False,
		)
		return len(serialized.encode('utf-8'))

	# Numbers / bool
	if isinstance(data, (int, float, bool)):
		return len(str(data).encode('utf-8'))

	# Fallback
	return len(str(data).encode('utf-8'))
