"""
This module contains the configuration logic
for Sentry integration in the Mwalika Agent system.
"""

import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import (
	FastApiIntegration,
)
from sentry_sdk.integrations.logging import (
	LoggingIntegration,
)


def init_sentry(
	dsn: str, environment: str, traces_sample_rate: float
) -> None:
	"""
	Initializes Sentry with the provided
	DSN and environment.
	"""
	sentry_sdk.init(
		dsn=dsn,
		environment=environment,
		integrations=[
			LoggingIntegration(
				# Capture all log levels
				# as breadcrumbs
				level=None,
				# Send events for ERROR and above
				event_level=logging.ERROR,
			),
			FastApiIntegration(),
		],
		send_default_pii=False,
		traces_sample_rate=traces_sample_rate,
	)
