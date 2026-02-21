"""
This module contains the EventForwarder class, which is
responsible for forwarding events to the appropriate
subscribers within the Mwalika Agent system.
"""

import asyncio
from typing import Any

import sentry_sdk

from api.lifecycle import (
	send_websocket_message_connection,
	send_websocket_message_user,
)
from events.lifecycle import get_next_event
from exceptions.core import ErrorContext
from exceptions.events import EventForwarderException
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.api.responses import WebSocketResponse
from schemas.events.core import EventType, InMemoryEvent


class EventForwarder:
	"""
	Responsible for forwarding events to
	the appropriate subscribers within the Mwalika
	Agent system.
	"""

	def __init__(self):
		# Start background task for processing events
		self._forwarder_task: asyncio.Task | None = None

	# --- Helper methods ---

	def _log_exception(
		self, message: str, code: str, cause: Exception
	):
		add_breadcrumb(
			category='event_forwarder',
			message=message,
			level=BreadcrumbLevel.ERROR,
			data={
				'error': str(cause),
				'code': code,
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
		raise EventForwarderException(
			message=message,
			code=code,
			context=ErrorContext(
				operation='event_forwarding',
				component='EventForwarder',
				metadata=meta,
			),
			cause=cause,
		) from cause

	# --- Lifecycle methods ---

	def start(self):
		if self._forwarder_task is not None:
			return  # Already started
		self._forwarder_task = asyncio.create_task(
			self._process_events()
		)

	async def stop(self):
		if self._forwarder_task is not None:
			self._forwarder_task.cancel()
			try:
				await self._forwarder_task
			except asyncio.CancelledError:
				# Task was cancelled, exit gracefully
				pass
			except Exception as e:
				self._log_exception(
					message=(
						'Unexpected error while stopping '
						'EventForwarder'
					),
					code='event_forwarder_stop_error',
					cause=e,
				)
			self._forwarder_task = None

	# --- WebSocket forwarding ---

	async def forward_ws_event(self, event: InMemoryEvent) -> None:
		try:
			user_id = event.user_id
			connection_id = event.event_options.get('connection_id')
			if not isinstance(event.payload, WebSocketResponse):
				raise ValueError(
					'Invalid payload type for WebSocket event'
				)

			if connection_id:
				# Forward to specific WebSocket connection
				await send_websocket_message_connection(
					user_id=user_id,
					connection_id=connection_id,
					message=event.payload,
				)
			else:
				# Broadcast to all WebSocket connections for the user
				await send_websocket_message_user(
					user_id=user_id, message=event.payload
				)
		except Exception as e:
			self._log_and_raise_exception(
				message=(
					'Failed to forward event to WebSocket subscribers'
				),
				code='ws_forwarding_error',
				cause=e,
				meta={
					'event_type': event.type,
					'event_id': event.event_id,
					'user_id': event.user_id,
				},
			)

	# --- Lifecycle consumer ---

	async def _process_events(self):
		try:
			while True:
				event = await get_next_event()
				if not event:
					# Sentinel value received, shutdown signal
					break

				# Handle event based on type and forward to
				# appropriate subscribers
				if event.type == EventType.WEBSOCKET_MESSAGE:
					await self.forward_ws_event(event)
				else:
					# Handle other event types as needed
					pass
		except asyncio.CancelledError:
			# Task was cancelled, exit gracefully
			pass
		except Exception as e:
			self._log_exception(
				message='Unexpected error in EventForwarder loop',
				code='event_forwarder_loop_error',
				cause=e,
			)
