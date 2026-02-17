"""
This file contains helper functions
for Sentry.
"""

from typing import Any

import sentry_sdk

# --- Constants --- #

_MAX_TAG_LEN = 64
_MAX_CRUMB_MSG = 120


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
	level: str = 'info',
	data: dict[str, Any] | None = None,
) -> None:
	msg = message.strip()
	if len(msg) > _MAX_CRUMB_MSG:
		msg = msg[:_MAX_CRUMB_MSG]

	sentry_sdk.add_breadcrumb(
		category=category,
		message=msg,
		level=level,
		data=data or {},
	)
