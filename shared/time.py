"""
This module contains shared time-related utilities
and constants for the Mwalika Agent system.
"""

from datetime import datetime, timezone


def get_timestamp() -> str:
	"""
	Returns the current timestamp in
	ISO 8601 format.
	"""
	return (
		datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
	)


def get_datetime(
	timestamp: str | None = None,
) -> datetime:
	"""
	Converts a timestamp string (ISO 8601
	format) to a datetime object if provided
	else returns current datetime.
	"""
	if not timestamp:
		return datetime.now(timezone.utc)
	return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
