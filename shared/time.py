"""
This module contains shared time-related utilities
and constants for the Mwalika Agent system.
"""

import time
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


def get_timestamp_s() -> int:
	"""
	Returns the current timestamp in seconds since epoch.
	"""
	return int(time.time())


def get_utc_day_key() -> str:
	"""
	Returns current UTC date in YYYY-MM-DD format.
	Example: "2026-02-24"
	"""
	return datetime.now(timezone.utc).date().isoformat()


def to_iso8601_z(
	value: datetime | int | float,
) -> str:
	"""
	Convert a datetime or Unix timestamp (seconds)
	into a UTC ISO8601 string with 'Z' suffix.
	"""

	if isinstance(value, (int, float)):
		dt = datetime.fromtimestamp(
			value,
			tz=timezone.utc,
		)
	elif isinstance(value, datetime):
		dt = value
		if dt.tzinfo is None:
			# Assume naive datetimes are UTC
			dt = dt.replace(tzinfo=timezone.utc)
		else:
			dt = dt.astimezone(timezone.utc)
	else:
		raise TypeError(
			f'Unsupported type for timestamp: {type(value)}'
		)

	return dt.isoformat().replace('+00:00', 'Z')
