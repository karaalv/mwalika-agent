"""
This module defines hooks related to Google Sheets
integration in the Mwalika Agent system.
"""

from os import getenv

import requests
from requests.exceptions import HTTPError

from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb_capture_exception,
)
from schemas.users.feedback import UserFeedback


def add_feedback_to_sheet(
	feedback: UserFeedback,
	timeout: float = 10.0,
) -> None:
	"""
	Send user feedback data to a Google Sheets endpoint.
	"""
	# Only attempt to send feedback to Google Sheets
	# if we are in production or a controlled development
	# environment
	mwalika_env = getenv('MWALIKA_ENV', '')
	if mwalika_env not in ['production', 'staging', 'development']:
		return

	try:
		google_sheets_endpoint = getenv('GOOGLE_SHEETS_FEEDBACK_URL')
		secret = getenv('GOOGLE_SHEETS_WEBHOOK_SECRET')
		if not google_sheets_endpoint or not secret:
			if not google_sheets_endpoint:
				raise ValueError(
					'Google Sheets endpoint URL is not configured'
				)
			if not secret:
				raise ValueError(
					'Google Sheets webhook secret is not configured'
				)
		url = f'{google_sheets_endpoint}?key={secret}'
		response = requests.post(
			url=url,
			json=feedback.model_dump(mode='json'),
			timeout=timeout,
		)
		response.raise_for_status()
	except HTTPError as http_err:
		add_breadcrumb_capture_exception(
			category='google_sheets_feedback',
			message=(
				'HTTP error occurred while '
				'sending feedback to Google Sheets'
				f': {http_err.response.reason}'
			),
			level=BreadcrumbLevel.ERROR,
			cause=http_err,
			data={
				'feedback_id': feedback.feedback_id,
				'code': http_err.response.status_code,
			},
		)
	except Exception as err:
		add_breadcrumb_capture_exception(
			category='google_sheets_feedback',
			message=(
				'Unexpected error occurred while '
				'sending feedback to Google Sheets'
				f': {err}'
			),
			level=BreadcrumbLevel.ERROR,
			cause=err,
			data={'feedback_id': feedback.feedback_id},
		)
