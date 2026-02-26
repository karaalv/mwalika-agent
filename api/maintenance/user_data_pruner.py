"""
This module contains the logic for the user data pruner,
which is responsible for periodically cleaning up expired user
data from the application across both database and in-memory
stores.
"""

import asyncio

from api.lifecycle.websocket_registry import (
	remove_users_websocket_connections,
)
from databases.mongodb.main import MongoDBCollection, get_collection
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb_capture_exception,
)
from shared.time import get_timestamp_s, to_iso8601_z


class UserDataPruner:
	"""
	This class is responsible for periodically pruning expired user
	data from the application across both database and in-memory
	stores.
	"""

	def __init__(self):
		# Pruning characteristics
		self.prune_interval_seconds = 24 * 60 * 60  # 24 hours
		self._inactivity_limit_seconds = 7 * 24 * 60 * 60  # 7 days
		self._db_batch_size = 500
		# Task management
		self._pruning_task: asyncio.Task | None = None
		self._lock = asyncio.Lock()
		# Prune state
		self._user_ids_to_prune: set[str] = set()

	# --- Lifecycle management ---

	def start(self):
		if self._pruning_task is None:
			self._pruning_task = asyncio.create_task(
				self._prune_loop()
			)

	async def stop(self):
		if self._pruning_task is not None:
			self._pruning_task.cancel()
			try:
				await self._pruning_task
			except asyncio.CancelledError:
				pass
			self._pruning_task = None

	# --- Pruning logic ---

	async def _prune_loop(self):
		try:
			while True:
				await self._fetch_inactive_users()
				await self._prune_user_data()
				await asyncio.sleep(self.prune_interval_seconds)
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=('Unexpected error in user data pruner loop'),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _fetch_inactive_users(self) -> None:
		"""
		Fetches the set of user IDs that have been inactive for
		longer than the inactivity limit from all relevant sources.
		"""
		await self._fetch_inactive_users_from_status()
		await self._fetch_inactive_users_from_anonymous()

	async def _fetch_inactive_users_from_status(self) -> None:
		"""
		Fetches the set of user IDs that have been inactive for
		longer than the inactivity limit.
		"""
		try:
			# First try fetching from usage stats data
			users_collection = get_collection(
				MongoDBCollection.USER_USAGE_STATS
			)
			cutoff_timestamp = (
				get_timestamp_s() - self._inactivity_limit_seconds
			)
			cursor = users_collection.find(
				{'last_api_request_at': {'$lt': cutoff_timestamp}},
				{'_id': 0, 'user_id': 1},
			)
			user_ids = {str(doc['user_id']) async for doc in cursor}
			# Add to prune set
			async with self._lock:
				self._user_ids_to_prune.update(user_ids)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=(
					'Failed to fetch inactive user IDs from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _fetch_inactive_users_from_anonymous(self) -> None:
		"""
		Fetches the set of user IDs that are marked as anonymous and
		have been inactive for longer than the inactivity limit.
		"""
		try:
			anonymous_collection = get_collection(
				MongoDBCollection.USERS
			)
			cutoff_timestamp_s = (
				get_timestamp_s() - self._inactivity_limit_seconds
			)
			cutoff_timestamp_str = to_iso8601_z(cutoff_timestamp_s)
			cursor = anonymous_collection.find(
				{'last_active_at': {'$lt': cutoff_timestamp_str}},
				{'_id': 0, 'user_id': 1},
			)
			user_ids = {str(doc['user_id']) async for doc in cursor}
			# Add to prune set
			async with self._lock:
				self._user_ids_to_prune.update(user_ids)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=(
					'Failed to fetch inactive anonymous '
					'user IDs from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _prune_user_data(self) -> None:
		"""
		Prunes all data associated with the user IDs in the prune set.
		"""
		async with self._lock:
			user_ids_to_prune = list(self._user_ids_to_prune)
			self._user_ids_to_prune.clear()
		if not user_ids_to_prune:
			return

		await asyncio.gather(
			self._delete_user_agent_sessions(user_ids_to_prune),
			self._delete_user_agent_memories(user_ids_to_prune),
			self._delete_user_data_record(user_ids_to_prune),
			self._remove_user_websocket_connections(
				user_ids_to_prune
			),
		)

	async def _delete_user_agent_sessions(
		self, user_ids: list[str]
	) -> None:
		"""
		Deletes all agent sessions associated with the given user IDs.
		"""
		try:
			collection = get_collection(MongoDBCollection.SESSIONS)
			for i in range(0, len(user_ids), self._db_batch_size):
				batch_user_ids = user_ids[i : i + self._db_batch_size]
				await collection.delete_many(
					{'user_id': {'$in': batch_user_ids}}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=(
					f'Failed to delete agent sessions '
					f'for {len(user_ids)} users'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _delete_user_agent_memories(
		self, user_ids: list[str]
	) -> None:
		"""
		Deletes all agent memories associated with the given user IDs.
		"""
		try:
			collection = get_collection(MongoDBCollection.MEMORIES)
			for i in range(0, len(user_ids), self._db_batch_size):
				batch_user_ids = user_ids[i : i + self._db_batch_size]
				await collection.delete_many(
					{'user_id': {'$in': batch_user_ids}}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=(
					f'Failed to delete agent memories '
					f'for {len(user_ids)} users'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _delete_user_data_record(
		self, user_ids: list[str]
	) -> None:
		"""
		Deletes the user data record associated with the
		given user IDs.
		"""
		try:
			collection = get_collection(MongoDBCollection.USERS)
			for i in range(0, len(user_ids), self._db_batch_size):
				batch_user_ids = user_ids[i : i + self._db_batch_size]
				await collection.delete_many(
					{'user_id': {'$in': batch_user_ids}}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=(
					f'Failed to delete user data records '
					f'for {len(user_ids)} users'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _remove_user_websocket_connections(
		self, user_ids: list[str]
	) -> None:
		"""
		Removes all active WebSocket connections associated with the
		given user IDs.
		"""
		try:
			await remove_users_websocket_connections(
				user_ids, reason='User data pruned due to inactivity'
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_data_pruner',
				message=(
					f'Failed to remove WebSocket connections '
					f'for {len(user_ids)} users'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)
