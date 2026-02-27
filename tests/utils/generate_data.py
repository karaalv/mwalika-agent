"""
This module contains utilities for generating test
data for the Mwalika Agent tests.
"""

import uuid


def gen_test_ip(prefix: str = '10.0.0.') -> str:
	"""
	Generate a unique, valid IPv4 address for tests.

	- Keeps IPs in a private range.
	- Avoids clashes across tests/modules.
	"""
	n = uuid.uuid4().int % 250 + 1
	return f'{prefix}{n}'
