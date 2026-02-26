"""
This module contains the logic for the limiter store pruner,
which is responsible for periodically cleaning up expired rate
limiters from the in-memory store to prevent memory bloat.
"""

import asyncio

from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb_capture_exception,
)
from security.ratelimit.store import (
	delete_limiters_by_keys,
	get_all_limiters,
)
from shared.time import get_timestamp_s


class LimiterStorePruner:
	"""
	This class is responsible for periodically
	pruning expired rate limiters from the in-memory store.
	"""

	def __init__(self):
		# Pruning characteristics
		self.prune_interval_seconds = 60 * 60  # 1 hour
		self._retention_time_seconds = 7 * 24 * 60 * 60  # 7 days
		# Task management
		self._pruning_task: asyncio.Task | None = None

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
				await asyncio.sleep(self.prune_interval_seconds)
				# Get all limiters and check for expiration
				limiters = await get_all_limiters()
				now = get_timestamp_s()
				keys_to_delete = []
				for key, limiter in limiters.items():
					if (
						now - limiter.created_at
						> self._retention_time_seconds
					):
						keys_to_delete.append(key)
				# Delete expired limiters
				if keys_to_delete:
					await delete_limiters_by_keys(keys_to_delete)
		except asyncio.CancelledError:
			# Task was cancelled, exit gracefully
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				cause=e,
				category='limiter_store_pruner',
				message='Error in limiter store pruner loop',
				level=BreadcrumbLevel.ERROR,
			)
