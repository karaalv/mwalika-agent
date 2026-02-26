"""
This file contains helper functions
for Sentry.
"""

from enum import Enum
from typing import Any

import sentry_sdk

# --- Constants --- #

_MAX_TAG_LEN = 64
_MAX_CRUMB_MSG = 120


class BreadcrumbLevel(Enum):
	INFO = 'info'
	ERROR = 'error'
	WARNING = 'warning'
	DEBUG = 'debug'


def set_tags(
	tags: dict[str, Any], metadata: dict | None = None
) -> None:
	"""
	Sets multiple tags in Sentry, long
	values are truncated.
	"""
	for k, v in tags.items():
		if v is None:
			continue
		val = str(v)
		if len(val) > _MAX_TAG_LEN:
			val = val[:_MAX_TAG_LEN]
		sentry_sdk.set_tag(k, val)

	if metadata:
		sentry_sdk.set_context('metadata', metadata)


def add_breadcrumb(
	category: str,
	message: str,
	level: BreadcrumbLevel = BreadcrumbLevel.INFO,
	data: dict[str, Any] | None = None,
) -> None:
	msg = message.strip()
	if len(msg) > _MAX_CRUMB_MSG:
		msg = msg[:_MAX_CRUMB_MSG]

	sentry_sdk.add_breadcrumb(
		category=category,
		message=msg,
		level=level.value,
		data=data or {},
	)


def add_breadcrumb_capture_exception(
	category: str,
	message: str,
	cause: Exception,
	level: BreadcrumbLevel = BreadcrumbLevel.ERROR,
	data: dict[str, Any] | None = None,
) -> None:
	add_breadcrumb(
		category=category,
		message=message,
		level=level,
		data=data,
	)
	sentry_sdk.capture_exception(cause)
