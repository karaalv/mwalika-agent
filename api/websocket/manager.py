"""
This module contains the WebSocketManager class,
which is responsible for managing the WebSocket
connection for a client interacting with the server.
"""

import asyncio

import sentry_sdk
from fastapi import WebSocket

from api.websocket.utils import create_websocket_response
from exceptions.api import WebSocketException
from exceptions.core import ErrorContext
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.api.responses import (
	WebSocketMessageType,
	WebSocketResponse,
)
from shared.ids import generate_uuid_str

# --- Constants ---

_MAX_QUEUE_SIZE = 333
_HEARTBEAT_INTERVAL_SECONDS = 30

# --- WebSocketManager class ---


class WebSocketManager:
	"""
	Manages the WebSocket connection
	for a client interacting with the server.
	"""

	def __init__(
		self, user_id: str, connection_id: str, websocket: WebSocket
	):
		# Websocket connection info
		self.user_id = user_id
		self.connection_id = connection_id
		self.websocket = websocket
		# To be set on each new request
		self.request_id = None
		# Message queue for buffering messages
		# (back-pressure)
		self._message_queue: asyncio.Queue[WebSocketResponse] = (
			asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
		)
		# Flag for tracking connection status
		self._is_closed = asyncio.Event()
		# Start background task for sending messages
		self._sender_task: asyncio.Task | None = None
		self._heartbeat_task: asyncio.Task | None = None

	# --- Helper methods ---

	def _raise_websocket_exception(
		self, message: str, code: str, cause: Exception
	):
		add_breadcrumb(
			category='websocket.manager',
			message=message,
			level=BreadcrumbLevel.ERROR,
			data={
				'user_id': self.user_id,
				'connection_id': self.connection_id,
				'request_id': self.request_id,
				'error': str(cause),
			},
		)
		sentry_sdk.capture_exception(cause)
		raise WebSocketException(
			message=message,
			code=code,
			context=ErrorContext(
				operation='websocket_operation',
				component='WebSocketManager',
				metadata={
					'user_id': self.user_id,
					'connection_id': self.connection_id,
					'request_id': self.request_id,
				},
			),
			cause=cause,
		) from cause

	def _log_exception(
		self, message: str, code: str, cause: Exception
	) -> None:
		add_breadcrumb(
			category='websocket.manager',
			message=message,
			level=BreadcrumbLevel.ERROR,
			data={
				'user_id': self.user_id,
				'connection_id': self.connection_id,
				'request_id': self.request_id,
				'code': code,
				'error': str(cause),
			},
		)
		sentry_sdk.capture_exception(cause)

	async def _log_and_close(
		self,
		message: str,
		code: str,
		cause: Exception,
		close_code: int = 1011,
	) -> None:
		self._log_exception(message=message, code=code, cause=cause)
		await self.close(
			code=close_code,
			reason=message,
		)

	# --- State management methods ---

	def start(self) -> None:
		"""
		Initializes the WebSocket connection and starts
		the background task for sending messages.
		"""
		self._sender_task = asyncio.create_task(
			self._message_sender()
		)
		self._heartbeat_task = asyncio.create_task(
			self._heartbeat_loop()
		)

	async def close(
		self, code: int = 1000, reason: str = 'Normal Closure'
	) -> None:
		"""
		Closes the WebSocket connection
		and performs any necessary cleanup.
		"""
		if self._is_closed.is_set():
			# Already closed, no action needed
			return
		self._is_closed.set()

		# Close background tasks
		if self._heartbeat_task:
			self._heartbeat_task.cancel()
		if self._sender_task:
			self._sender_task.cancel()

		try:
			await self.websocket.close(code=code, reason=reason)
		except Exception as e:
			self._log_exception(
				message='Failed to close WebSocket connection',
				code='websocket_close_error',
				cause=e,
			)

	async def _heartbeat_loop(self) -> None:
		"""
		Periodically sends heartbeat messages to
		the client to keep the connection alive and detect
		disconnections.
		"""
		try:
			while not self._is_closed.is_set():
				heartbeat_message = create_websocket_response(
					message_type=WebSocketMessageType.HEARTBEAT,
					payload='ping',
					request_id=generate_uuid_str(),
					success=True,
					message='Heartbeat ping',
				)
				await self.send_message(heartbeat_message)
				await asyncio.sleep(_HEARTBEAT_INTERVAL_SECONDS)
		except asyncio.CancelledError:
			# Task was cancelled, exit gracefully
			pass
		except Exception as e:
			self._log_exception(
				message=(
					'Unexpected error in WebSocket heartbeat loop'
				),
				code='websocket_heartbeat_error',
				cause=e,
			)
			await self.close(
				code=1011,
				reason=(
					'Unexpected error in WebSocket heartbeat loop'
				),
			)

	# --- Message handling methods ---

	async def send_message(self, response: WebSocketResponse) -> None:
		"""
		Sends a message to the client over the
		WebSocket connection.
		"""
		if self._is_closed.is_set():
			return
		try:
			# Queue message based on type
			if (
				response.message.type
				== WebSocketMessageType.HEARTBEAT
			):
				# Heartbeat messages are sent immediately
				try:
					await self._message_queue.put(response)
				except asyncio.QueueFull as e:
					# If queue is full, close
					# connection to prevent resource exhaustion
					await self._log_and_close(
						message=(
							'Message queue full, closing '
							'WebSocket connection'
						),
						code='websocket_queue_full',
						cause=e,
						close_code=1013,
					)
			else:
				# Other messages are enqueued for sending
				await self._message_queue.put(response)
		except Exception as e:
			self._log_exception(
				message=(
					'Failed to enqueue message '
					'for WebSocket connection'
				),
				code='websocket_enqueue_error',
				cause=e,
			)

	async def _message_sender(self) -> None:
		"""
		Background task that continuously sends messages
		from the queue to the client until the connection
		is closed.
		"""
		try:
			while not self._is_closed.is_set():
				response = await self._message_queue.get()
				# Set request_id for logging context
				self.request_id = response.meta.request_id
				try:
					await self.websocket.send_json(
						response.model_dump(mode='json')
					)
				except Exception as e:
					await self._log_and_close(
						message=(
							'Failed to send message over WebSocket '
							'connection'
						),
						code='websocket_send_error',
						cause=e,
					)
					break
		except asyncio.CancelledError:
			# Task was cancelled, exit gracefully
			pass
		except Exception as e:
			await self._log_and_close(
				message=(
					'Unexpected error in WebSocket message sender'
				),
				code='websocket_sender_error',
				cause=e,
			)
