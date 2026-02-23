"""
This module defines the WebSocketRegistry which is
responsible for managing active WebSocket connections
per user.

Design:
- user_id -> connection_id -> WebSocketManager
- asyncio.Lock protects in-memory state
"""

import asyncio

import sentry_sdk
from fastapi import WebSocket

from api.websocket.manager import WebSocketManager
from exceptions.api import WebSocketRegistryException
from exceptions.core import ErrorContext
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
)
from schemas.api.responses import WebSocketResponse


class WebSocketRegistry:
	"""
	Manages active WebSocket connections per user.
	"""

	def __init__(self):
		# user_id -> connection_id -> WebSocketManager
		self._registry: dict[str, dict[str, WebSocketManager]] = {}
		# Lock to protect in-memory state
		self._lock = asyncio.Lock()

	# --- Helper methods ---

	def _log_exception(
		self, message: str, code: str, cause: Exception
	):
		add_breadcrumb(
			category='websocket.registry',
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
		meta: dict[str, str] | None = None,
	):
		self._log_exception(message=message, code=code, cause=cause)
		raise WebSocketRegistryException(
			message=message,
			code=code,
			context=ErrorContext(
				operation='websocket_registry_operation',
				component='WebSocketRegistry',
				metadata=meta or {},
			),
			cause=cause,
		) from cause

	# --- Query methods ---

	async def has_user(self, user_id: str) -> bool:
		async with self._lock:
			return user_id in self._registry

	async def has_connection(
		self, user_id: str, connection_id: str
	) -> bool:
		async with self._lock:
			return (
				user_id in self._registry
				and connection_id in self._registry[user_id]
			)

	async def get_connection(
		self, user_id: str, connection_id: str
	) -> WebSocketManager | None:
		async with self._lock:
			if user_id in self._registry:
				return self._registry[user_id].get(connection_id)
			return None

	async def count_connections(self, user_id: str) -> int:
		async with self._lock:
			if user_id in self._registry:
				return len(self._registry[user_id])
			return 0

	# --- Lifecycle methods ---

	async def add_connection(
		self, user_id: str, connection_id: str, websocket: WebSocket
	) -> WebSocketManager | None:
		"""
		Adds a new WebSocket connection for the given
		user and connection ID.
		"""
		try:
			manager = WebSocketManager(
				user_id, connection_id, websocket
			)
			# Start the manager's background tasks
			manager.start()
			async with self._lock:
				self._registry.setdefault(user_id, {})
				self._registry[user_id][connection_id] = manager
			return manager
		except Exception as e:
			self._log_and_raise_exception(
				message=(
					'Failed to add WebSocket '
					'connection to registry '
					f'for user {user_id} and connection '
					f'{connection_id}'
				),
				code='websocket_add_connection_error',
				cause=e,
			)

	async def remove_connection(
		self,
		user_id: str,
		connection_id: str,
		reason: str = 'Normal closure',
		close_code: int = 1000,
	):
		"""
		Removes a WebSocket connection for the given
		user and connection ID.
		"""
		manager: WebSocketManager | None = None
		async with self._lock:
			if (
				user_id in self._registry
				and connection_id in self._registry[user_id]
			):
				manager = self._registry[user_id][connection_id]
				del self._registry[user_id][connection_id]
				# Clean up user entry if no more connections
				if not self._registry[user_id]:
					del self._registry[user_id]

		# Close manager outside of lock to avoid
		# blocking other operations
		if manager:
			try:
				await manager.close(reason=reason, code=close_code)
			except Exception:
				# Let manager handle exceptions
				pass

	async def remove_user_connections(
		self,
		user_id: str,
		reason: str = 'Normal closure',
		close_code: int = 1000,
	):
		"""
		Removes all WebSocket connections for the given user.
		"""
		managers: list[WebSocketManager] = []
		async with self._lock:
			if user_id in self._registry:
				managers = list(self._registry[user_id].values())
				del self._registry[user_id]

		# Close managers outside of lock to avoid
		# blocking other operations
		for manager in managers:
			try:
				await manager.close(reason=reason, code=close_code)
			except Exception:
				# Let manager handle exceptions
				pass

	async def close_all_connections(
		self, reason: str = 'Normal closure', close_code: int = 1000
	):
		"""
		Closes all WebSocket connections in the registry.
		"""
		managers: list[WebSocketManager] = []
		async with self._lock:
			for user_id in list(self._registry.keys()):
				managers.extend(self._registry[user_id].values())
			self._registry.clear()

		# Close managers outside of lock to avoid
		# blocking other operations
		for manager in managers:
			try:
				await manager.close(reason=reason, code=close_code)
			except Exception:
				# Let manager handle exceptions
				pass

	# --- Message sending methods ---

	async def send_user(
		self, user_id: str, message: WebSocketResponse
	) -> None:
		"""
		Sends a message to all WebSocket connections for the
		given user.
		"""
		managers: list[WebSocketManager] = []
		async with self._lock:
			if user_id in self._registry:
				managers = list(self._registry[user_id].values())

		# Send messages outside of lock to avoid blocking
		for manager in managers:
			try:
				await manager.send_message(message)
			except Exception:
				# Let manager handle exceptions
				pass

	async def send_connection(
		self,
		user_id: str,
		connection_id: str,
		message: WebSocketResponse,
	) -> None:
		"""
		Sends a message to a specific WebSocket connection
		for the given user and connection ID.
		"""
		manager: WebSocketManager | None = None
		async with self._lock:
			if user_id in self._registry:
				manager = self._registry[user_id].get(connection_id)

		if manager:
			try:
				await manager.send_message(message)
			except Exception:
				# Let manager handle exceptions
				pass
