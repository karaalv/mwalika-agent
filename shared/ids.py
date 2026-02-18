from uuid import uuid4


def generate_uuid_str() -> str:
	"""
	Generate a random UUID4 string suitable
	for Qdrant point IDs.
	"""
	return uuid4().hex
