"""
This module contains the EventBus class, which is
a simple in memory event bus implementation used for managing
events and subscriptions within the Mwalika Agent system.
"""

import asyncio
from typing import Any

import sentry_sdk

from exceptions.core import ErrorContext
from exceptions.events import EventBusException
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.events.core import InMemoryEvent

# --- Constants ---

_MAX_QUEUE_SIZE = 30_000


class InMemoryBus:
	"""
	A simple in-memory event bus implementation that allows
	for subscribing to events and publishing events to
	subscribers.
	"""

	def __init__(self):
		# Message queue for events
		self._event_queue: asyncio.Queue[InMemoryEvent | None] = (
			asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
		)

	# --- Helper methods ---

	def _log_exception(
		self, message: str, code: str, cause: Exception
	):
		add_breadcrumb(
			category='event_bus',
			message=message,
			level=BreadcrumbLevel.ERROR,
			data={
				'error': str(cause),
				'code': code,
				'queue_size': self._event_queue.qsize(),
			},
		)
		sentry_sdk.capture_exception(cause)

	def _log_and_raise_exception(
		self,
		message: str,
		code: str,
		cause: Exception,
		meta: dict[str, Any] | None = None,
	):
		self._log_exception(message, code, cause)
		raise EventBusException(
			message=message,
			code=code,
			cause=cause,
			context=ErrorContext(
				operation='event_bus_operation',
				component='InMemoryBus',
				metadata=meta,
			),
		) from cause

	# --- Lifecycle methods ---

	def start(self):
		# No initialization needed for
		# in-memory bus
		pass

	async def stop(self):
		"""
		Closes the event bus and releases any
		consumers by putting a sentinel value in the
		queue.
		"""
		await self.publish(None)

	# --- Event management methods ---

	async def publish(self, event: InMemoryEvent | None):
		try:
			await self._event_queue.put(event)
		except Exception as e:
			self._log_exception(
				message='Failed to publish event to bus',
				code='publish_error',
				cause=e,
			)

	async def get_event(self) -> InMemoryEvent | None:
		try:
			event = await self._event_queue.get()
			return event
		except Exception as e:
			self._log_and_raise_exception(
				message='Failed to retrieve event from bus',
				code='get_event_error',
				cause=e,
			)
