"""
This module contains the configuration logic
for Sentry integration in the Mwalika Agent system.
"""

import logging
from os import getenv

import sentry_sdk
from sentry_sdk.integrations.fastapi import (
	FastApiIntegration,
)
from sentry_sdk.integrations.logging import (
	LoggingIntegration,
)

from exceptions.core import ErrorContext
from exceptions.services import SentryException
from shared.logging import LogStyle, cprint

# --- Configuration ---

_SENTRY_DSN = getenv('SENTRY_DSN', '')
_SENTRY_ENVIRONMENT = getenv('MWALIKA_ENV', '')
_SENTRY_TRACES_SAMPLE_RATE = float(
	getenv('SENTRY_TRACES_SAMPLE_RATE', '')
)


def init_sentry(
	dsn: str = _SENTRY_DSN,
	environment: str = _SENTRY_ENVIRONMENT,
	traces_sample_rate: float = _SENTRY_TRACES_SAMPLE_RATE,
) -> None:
	"""
	Initializes Sentry with the provided
	DSN and environment.
	"""
	# Check for required configuration
	if not dsn:
		raise SentryException(
			message=('SENTRY_DSN environment variable must be set.'),
			code='sentry_config_incomplete',
			context=ErrorContext(
				operation='init_sentry',
				component='sentry.config',
			),
		)

	if not environment:
		raise SentryException(
			message=(
				'MWALIKA_ENV environment variable '
				'must be set for Sentry environment.'
			),
			code='sentry_environment_incomplete',
			context=ErrorContext(
				operation='init_sentry',
				component='sentry.config',
			),
		)

	if traces_sample_rate < 0.0 or traces_sample_rate > 1.0:
		raise SentryException(
			message=(
				'SENTRY_TRACES_SAMPLE_RATE must be '
				'between 0.0 and 1.0.'
			),
			code='sentry_traces_sample_rate_invalid',
			context=ErrorContext(
				operation='init_sentry',
				component='sentry.config',
				metadata={
					'SENTRY_TRACES_SAMPLE_RATE': traces_sample_rate
				},
			),
		)

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

	cprint(
		'Sentry initialized successfully.',
		style=LogStyle.SUCCESS,
		prefix='sentry.config',
	)
