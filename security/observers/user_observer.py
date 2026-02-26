"""
This module defines the user observer for the Mwalika
Agent system, which is responsible for monitoring user
activity, tracking usage statistics, and enforcing security
measures such as rate limiting and blocking based on behavior.
"""

import asyncio

from pymongo import UpdateOne

from databases.mongodb.main import MongoDBCollection, get_collection
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb_capture_exception,
)
from schemas.security.observers import (
	BlockedEntity,
	BlockedEntityType,
	DbWriteBackTask,
	DbWriteBackTaskType,
	MinuteCounter,
)
from schemas.security.users import UserUsageStats
from security.config.observers import (
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3,
	FORGIVENESS_PERIOD_SECONDS,
	HOURS_IN_SECONDS_24,
	MAX_DAILY_AGENT_INPUT_TOKENS_PER_USER,
	MAX_DAILY_AT_GENERATED_PER_USER,
	MAX_DAILY_BAD_REQUESTS_PER_USER,
	MAX_DAILY_CLAIM_COOKIES_PER_USER,
	MAX_DAILY_REQUESTS_PER_USER,
	MAX_PER_MINUTE_REQUESTS_PER_USER,
	MAX_WS_CONNECTIONS_PER_USER,
	USER_BLOCK_DURATION_LV_1,
	USER_BLOCK_DURATION_LV_2,
	USER_BLOCK_DURATION_LV_3,
	WS_BLOCK_DURATION_LV_1,
	WS_BLOCK_DURATION_LV_2,
	WS_BLOCK_DURATION_LV_3,
)
from shared.time import get_timestamp_s, get_utc_day_key


class UserObserver:
	"""
	The user observer class responsible for
	monitoring user activity, tracking usage statistics,
	and helping enforce security measures.

	NOTE: Only public methods should use the lock at the top
	level. Internal helper methods can assume they are called
	within a locked context when needed, to avoid unnecessary
	locking and unlocking within the same flow.
	"""

	def __init__(self):
		# Main state for tracking user usage stats,
		# keyed by user ID
		self._user_stats: dict[str, UserUsageStats] = {}
		self._blocked_users: dict[str, BlockedEntity] = {}
		self._rate_limit_tracker: dict[str, MinuteCounter] = {}
		# Lock for concurrent access to user stats and blocked users
		self._lock = asyncio.Lock()
		# Used for periodic pushes of stats to the database
		self._users_to_update: set[str] = set()
		self._update_interval_seconds = 60
		self._max_size_to_force_push = 50
		self._last_update_time = get_timestamp_s()
		self._schedule_task: asyncio.Task | None = None
		self._db_write_back_task: asyncio.Task | None = None
		self._db_write_back_queue: asyncio.Queue[DbWriteBackTask] = (
			asyncio.Queue(maxsize=1_000)
		)
		# Used for cleanup
		self._cleanup_interval_seconds = 60 * 60  # 1 hour
		self._persistence_time_s = (
			7 * 24 * 60 * 60
		)  # 7 days in seconds
		self._deletion_batch_size = 250
		self._cleanup_task: asyncio.Task | None = None

	# --- Observer lifecycle management ---

	async def start(self) -> None:
		"""
		Starts the user observer, including any background
		tasks needed for periodic database updates or other
		maintenance tasks.
		"""
		if self._schedule_task is None:
			self._schedule_task = asyncio.create_task(
				self._periodic_stats_push()
			)

		if self._db_write_back_task is None:
			self._db_write_back_task = asyncio.create_task(
				self._process_db_write_back_tasks()
			)

		if self._cleanup_task is None:
			self._cleanup_task = asyncio.create_task(
				self._periodic_cleanup()
			)

		# Load currently blocked users from the database
		await self._load_blocked_users_from_db()

	async def stop(self) -> None:
		"""
		Stops the user observer and cancels any background
		tasks to ensure a clean shutdown.
		"""
		if self._schedule_task is not None:
			self._schedule_task.cancel()
			try:
				await self._schedule_task
			except asyncio.CancelledError:
				pass

		if self._db_write_back_task is not None:
			self._db_write_back_task.cancel()
			try:
				await self._db_write_back_task
			except asyncio.CancelledError:
				pass

		if self._cleanup_task is not None:
			self._cleanup_task.cancel()
			try:
				await self._cleanup_task
			except asyncio.CancelledError:
				pass

		self._schedule_task = None
		self._db_write_back_task = None
		self._cleanup_task = None

	async def _load_blocked_users_from_db(self) -> None:
		"""
		Loads currently blocked users from the database into memory
		on startup, which allows the observer to enforce blocks that
		were active before a restart.
		"""
		try:
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			cursor = blocked_entities_collection.find(
				{'entity_type': BlockedEntityType.USER}
			)
			async for doc in cursor:
				blocked_entity = BlockedEntity.model_validate(doc)
				self._blocked_users[blocked_entity.entity_id] = (
					blocked_entity
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_load_blocked_users',
				message='Failed to load blocked users from database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)
			raise e

	# --- Database push management ---

	def _add_user_to_update(self, user_id: str) -> None:
		"""
		Marks a user's stats as needing to be pushed to the database.
		This should be called whenever a user's stats are updated to
		ensure that the latest stats are eventually persisted.
		"""
		self._users_to_update.add(user_id)

	async def _push_stats_to_db(self) -> None:
		"""
		Pushes the latest user stats to the database for persistence
		and analytics. This method is called periodically or when the
		number of pending updates exceeds a certain threshold.
		"""
		async with self._lock:
			if not self._users_to_update:
				return  # No updates to push

			users_to_update = list(self._users_to_update)
			user_stats_snapshot = {
				user_id: self._user_stats[user_id]
				for user_id in users_to_update
				if user_id in self._user_stats
			}
			self._users_to_update.clear()

		try:
			usage_stats_collection = await get_collection(
				MongoDBCollection.USER_USAGE_STATS
			)
			# Prepare bulk update operations
			bulk_ops = []
			for user_id in users_to_update:
				if user_id in user_stats_snapshot:
					stats = user_stats_snapshot[user_id]
					bulk_ops.append(
						UpdateOne(
							filter={'user_id': user_id},
							update={
								'$set': stats.model_dump(mode='json')
							},
							upsert=True,
						)
					)
			if bulk_ops:
				await usage_stats_collection.bulk_write(bulk_ops)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_db_push',
				message='Failed to push user stats to database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
				data={'num_users': len(users_to_update)},
			)
			# If the database push fails, re-add the users
			# to the update set to try again on the next interval
			async with self._lock:
				self._users_to_update.update(users_to_update)

	async def _periodic_stats_push(self) -> None:
		"""
		Schedules a push of user stats to the database if the update
		interval has passed or if the number of pending updates
		exceeds the threshold.
		"""
		try:
			while True:
				current_time = get_timestamp_s()
				time_since_last_update = (
					current_time - self._last_update_time
				)
				if (
					time_since_last_update
					>= self._update_interval_seconds
					or len(self._users_to_update)
					>= self._max_size_to_force_push
				):
					await self._push_stats_to_db()
					self._last_update_time = current_time
				await asyncio.sleep(1)
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_scheduler',
				message='Error in user stats push scheduler',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _process_db_write_back_tasks(self):
		"""
		Continuously processes database write-back tasks from the
		queue, which are used to perform database operations related
		to blocking and unblocking users based on the defined
		tasks.
		"""
		try:
			while True:
				task = await self._db_write_back_queue.get()
				try:
					if (
						task.task_type
						== DbWriteBackTaskType.PUSH_BLOCKED_ENTITY
					):
						if task.blocked_entity:
							await self._push_blocked_user_to_db(
								task.blocked_entity
							)
					elif (
						task.task_type
						== DbWriteBackTaskType.DELETE_BLOCKED_ENTITY
					):
						if task.blocked_entity:
							await self._remove_blocked_user_from_db(
								task.blocked_entity.entity_id
							)
				except Exception as e:
					blocked_entity = (
						task.blocked_entity.model_dump()
						if task.blocked_entity
						else None
					)
					add_breadcrumb_capture_exception(
						category='user_observer_db_write_back',
						message=(
							'Error in processing DB write-back task'
						),
						cause=e,
						level=BreadcrumbLevel.ERROR,
						data={
							'task_type': task.task_type,
							'blocked_entity': blocked_entity,
						},
					)
				finally:
					self._db_write_back_queue.task_done()
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_db_write_back',
				message='Error in processing DB write-back tasks',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _push_blocked_user_to_db(
		self, blocked_entity: BlockedEntity
	) -> None:
		"""
		Pushes a blocked entity record to the database for persistence
		and analytics, which can be used to track blocked users, IP
		addresses, or tokens over time.
		"""
		try:
			# Push to database
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			await blocked_entities_collection.update_one(
				{
					'entity_id': blocked_entity.entity_id,
					'entity_type': blocked_entity.entity_type,
				},
				{'$set': blocked_entity.model_dump(mode='json')},
				upsert=True,
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_db_push_block',
				message='Failed to push blocked entity to database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
				data={
					'entity_type': blocked_entity.entity_type,
					'entity_id': blocked_entity.entity_id,
				},
			)

	async def _remove_blocked_user_from_db(
		self, user_id: str
	) -> None:
		"""
		Removes the blocked user record for the given user ID from the
		database, which can be used for cleanup of old records or in
		response to data retention policies.
		"""
		try:
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			await blocked_entities_collection.delete_one(
				{
					'entity_id': user_id,
					'entity_type': BlockedEntityType.USER,
				}
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_db_delete_block',
				message=(
					'Failed to remove blocked entity from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
				data={
					'entity_type': BlockedEntityType.USER,
					'entity_id': user_id,
				},
			)

	async def _wait_for_db_task_queue(
		self, tasks: list[DbWriteBackTask]
	):
		"""
		Waits for the database write-back task queue to have capacity
		and then places the given tasks in the queue to be processed.
		"""
		try:
			for task in tasks:
				await asyncio.wait_for(
					self._db_write_back_queue.put(task),
					timeout=1.0,
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_db_write_back_timeout',
				message=(
					'Database write-back queue timeout, '
					'failed to enqueue task'
				),
				cause=e,
				level=BreadcrumbLevel.WARNING,
			)

	# --- User blocking management ---

	def _get_user_block_count(self, user_id: str) -> int:
		"""
		Returns the number of times the user has been blocked,
		which can be useful for monitoring repeat offenders and
		enforcing escalating consequences for repeated violations
		of security policies.
		"""
		if user_id in self._user_stats:
			return self._user_stats[user_id].blocked_count
		return 0

	def _update_last_blocked_at(self, user_id: str) -> None:
		"""
		Updates the timestamp of the user's last block, which can be
		useful for tracking block durations and managing data
		retention policies.
		"""
		if user_id in self._user_stats:
			self._user_stats[
				user_id
			].last_blocked_at = get_timestamp_s()

	def _block_user(
		self, user_id: str, reason: str, duration_seconds: int
	) -> DbWriteBackTask:
		"""
		Internal method to block a user for a specified duration
		with a given reason, which can be used to enforce temporary
		blocks based on specific policy violations or behavior.
		"""
		prev_block_count = self._get_user_block_count(user_id)
		if user_id not in self._user_stats:
			self._user_stats[user_id] = UserUsageStats(
				user_id=user_id,
				day_key=get_utc_day_key(),
			)
		self._user_stats[user_id].blocked_count = prev_block_count + 1
		self._update_last_blocked_at(user_id)
		# If user is already blocked, keep longest block duration
		# and update reason to reflect latest violation
		if user_id in self._blocked_users:
			existing_block = self._blocked_users[user_id]
			if existing_block.blocked_until > get_timestamp_s():
				# Update reason to reflect latest violation
				reason = f'{existing_block.reason}; {reason}'
				duration_seconds = max(
					existing_block.blocked_until - get_timestamp_s(),
					duration_seconds,
				)
		self._blocked_users[user_id] = BlockedEntity(
			entity_type=BlockedEntityType.USER,
			entity_id=user_id,
			reason=reason,
			blocked_until=get_timestamp_s() + duration_seconds,
		)

		# Return database write-back to place
		# in queue outside lock
		return DbWriteBackTask(
			task_type=DbWriteBackTaskType.PUSH_BLOCKED_ENTITY,
			blocked_entity=self._blocked_users[user_id].model_copy(),
		)

	def _reset_and_unblock_user_if_new_day(
		self, user_id: str
	) -> DbWriteBackTask | None:
		"""
		Resets the user's daily stats and unblocks them if a new day
		has started, which can be used to enforce daily limits and
		ensure accurate tracking of user activity.
		"""
		self._reset_user_stats_if_new_day(user_id)
		return self._unblock_user_if_block_expired(user_id)

	def _unblock_user_if_block_expired(
		self, user_id: str
	) -> DbWriteBackTask | None:
		"""
		Unblocks the user if their block duration has expired,
		which can be used to automatically lift blocks after the
		specified duration has passed without requiring manual
		intervention.
		"""
		# Delete the block if the block duration has expired
		if user_id in self._blocked_users:
			blocked_entity = self._blocked_users[user_id].model_copy()
			if get_timestamp_s() >= blocked_entity.blocked_until:
				del self._blocked_users[user_id]

				# Return database write-back to place in
				# queue outside lock
				return DbWriteBackTask(
					task_type=DbWriteBackTaskType.DELETE_BLOCKED_ENTITY,
					blocked_entity=blocked_entity,
				)

	def _reset_user_stats_if_new_day(self, user_id: str) -> None:
		"""
		Resets the user's daily stats if a new day has started, which
		can be used to enforce daily limits and ensure that usage
		tracking is accurate across day boundaries.
		"""
		current_day_key = get_utc_day_key()
		if (
			user_id in self._user_stats
			and self._user_stats[user_id].day_key != current_day_key
		):
			stats = self._user_stats[user_id]
			# Resets for new day
			stats.day_key = current_day_key
			stats.requests_today = 0
			stats.bad_requests_today = 0
			stats.agent_input_tokens_today = 0

			# Reset block count if forgiveness period has
			# passed since last block
			if stats.last_blocked_at:
				time_since_last_block = (
					get_timestamp_s() - stats.last_blocked_at
				)
				if time_since_last_block > FORGIVENESS_PERIOD_SECONDS:
					stats.blocked_count = 0

	def _resolve_user_block_duration(self, block_count: int) -> int:
		"""
		Resolves the block duration for a user based on their block
		count which can be used to enforce escalating consequences for
		repeated violations of security policies.
		"""
		if block_count == 0:
			return USER_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return USER_BLOCK_DURATION_LV_2
		else:
			return USER_BLOCK_DURATION_LV_3

	def _resolve_agent_input_token_block_duration(
		self, block_count: int
	) -> int:
		"""
		Resolves the block duration for a user based on their block
		count which can be used to enforce escalating consequences for
		repeated violations of security policies related to agent
		input token usage.
		"""
		if block_count == 0:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2
		else:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3

	def _resolve_ws_block_duration(self, block_count: int) -> int:
		"""
		Resolves the block duration for a user based on their block
		count which can be used to enforce escalating consequences for
		repeated violations of security policies related to WebSocket
		connection usage.
		"""
		if block_count == 0:
			return WS_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return WS_BLOCK_DURATION_LV_2
		else:
			return WS_BLOCK_DURATION_LV_3

	# --- User status inspection ---

	async def is_user_blocked(
		self, user_id: str
	) -> BlockedEntity | None:
		"""
		Checks if the user is currently blocked based on their
		activity and usage patterns, which can be used to
		prevent interactions with agents if they have exceeded
		limits or exhibited suspicious behavior.
		"""
		db_write_back_tasks = []
		async with self._lock:
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)
			result = self._blocked_users.get(user_id)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

		# Return block status result
		return result

	# --- Public status update methods ---

	def _increment_and_check_rate_limit(
		self, user_id: str
	) -> DbWriteBackTask | None:
		"""
		Increments the user's request count and checks if they have
		exceeded any rate limits, which can be used to enforce limits
		on API usage and prevent abuse by blocking users who exceed
		defined thresholds for requests or other tracked metrics.
		"""
		current_time_s = get_timestamp_s()
		min_key = current_time_s - (current_time_s % 60)

		if user_id not in self._rate_limit_tracker:
			self._rate_limit_tracker[user_id] = MinuteCounter(
				minute_key=min_key, count=1
			)
		else:
			tracker = self._rate_limit_tracker[user_id]
			if tracker.minute_key == min_key:
				tracker.count += 1
			else:
				tracker.minute_key = min_key
				tracker.count = 1

		# If user exceeds per-minute request limit, block them
		if (
			self._rate_limit_tracker[user_id].count
			> MAX_PER_MINUTE_REQUESTS_PER_USER
		):
			duration = self._resolve_user_block_duration(
				self._get_user_block_count(user_id)
			)
			return self._block_user(
				user_id,
				reason=(
					f'Exceeded per-minute request limit, '
					f'blocked for {duration // 60} minutes'
				),
				duration_seconds=duration,
			)

	async def update_latest_request(
		self, user_id: str
	) -> BlockedEntity | None:
		"""
		Updates the timestamp of the user's latest request
		and increments their request count for today.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id not in self._user_stats:
				self._user_stats[user_id] = UserUsageStats(
					user_id=user_id, day_key=get_utc_day_key()
				)
			stats = self._user_stats[user_id]
			stats.requests_today += 1
			stats.last_api_request_at = get_timestamp_s()

			# Mark update
			self._add_user_to_update(user_id)

			# Check if user exceeds per-minute request limit
			rl_block_task = self._increment_and_check_rate_limit(
				user_id
			)
			req_block_task = None

			# If user exceeds daily request limit,
			# add to blocked users
			if stats.requests_today > MAX_DAILY_REQUESTS_PER_USER:
				req_block_task = self._block_user(
					user_id,
					reason=(
						f'Exceeded daily request limit, '
						f'blocked for {HOURS_IN_SECONDS_24 // 3600} '
						f'hours'
					),
					duration_seconds=HOURS_IN_SECONDS_24,
				)
			if rl_block_task and not req_block_task:
				db_write_back_tasks.append(rl_block_task)
				block = rl_block_task.blocked_entity
			elif req_block_task:
				db_write_back_tasks.append(req_block_task)
				block = req_block_task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def add_bad_request(
		self, user_id: str
	) -> BlockedEntity | None:
		"""
		Increments the count of bad requests made by the user today,
		which can be used to identify potentially malicious behavior.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id not in self._user_stats:
				self._user_stats[user_id] = UserUsageStats(
					user_id=user_id, day_key=get_utc_day_key()
				)
			stats = self._user_stats[user_id]
			stats.bad_requests_today += 1

			# Mark update
			self._add_user_to_update(user_id)

			# If user exceeds bad request limit, add to blocked users
			if (
				stats.bad_requests_today
				> MAX_DAILY_BAD_REQUESTS_PER_USER
			):
				task = self._block_user(
					user_id,
					reason=(
						f'Exceeded bad request limit, '
						f'blocked for {HOURS_IN_SECONDS_24 // 3600} '
						f'hours'
					),
					duration_seconds=HOURS_IN_SECONDS_24,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def add_ws_connection(
		self, user_id: str, connection_id: str
	) -> BlockedEntity | None:
		"""
		Adds an active WebSocket connection ID to the user's stats,
		which can be used to manage real-time interactions and enforce
		limits on concurrent connections.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id not in self._user_stats:
				self._user_stats[user_id] = UserUsageStats(
					user_id=user_id, day_key=get_utc_day_key()
				)
			stats = self._user_stats[user_id]
			if connection_id not in stats.active_ws_connections:
				stats.active_ws_connections.append(connection_id)

			# Mark update
			self._add_user_to_update(user_id)

			# If user exceeds max WebSocket connections,
			# add to blocked users
			if (
				len(stats.active_ws_connections)
				> MAX_WS_CONNECTIONS_PER_USER
			):
				duration = self._resolve_ws_block_duration(
					self._get_user_block_count(user_id)
				)

				task = self._block_user(
					user_id,
					reason=(
						f'Exceeded maximum WebSocket connections, '
						f'blocked for {duration // 60} minutes'
					),
					duration_seconds=duration,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def remove_ws_connection(
		self, user_id: str, connection_id: str
	) -> None:
		"""
		Removes a WebSocket connection ID from the user's stats,
		which should be called when a WebSocket connection is closed
		to keep the active connections list accurate.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Update stats
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id in self._user_stats:
				stats = self._user_stats[user_id]
				if connection_id in stats.active_ws_connections:
					stats.active_ws_connections.remove(connection_id)
					# Mark update
					self._add_user_to_update(user_id)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	async def add_agent_input_tokens(
		self, user_id: str, token_count: int
	) -> BlockedEntity | None:
		"""
		Increments the total number of input tokens sent to agents
		by the user and updates the count for today, which can be
		used to enforce token-based rate limits.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id not in self._user_stats:
				self._user_stats[user_id] = UserUsageStats(
					user_id=user_id, day_key=get_utc_day_key()
				)
			stats = self._user_stats[user_id]
			stats.agent_input_tokens_today += max(token_count, 0)

			# Mark update
			self._add_user_to_update(user_id)

			# Check if user exceeds per-minute request limit
			rl_block_task = self._increment_and_check_rate_limit(
				user_id
			)
			req_block_task = None

			# Check if user exceeds daily token limit
			if (
				stats.agent_input_tokens_today
				> MAX_DAILY_AGENT_INPUT_TOKENS_PER_USER
			):
				duration = (
					self._resolve_agent_input_token_block_duration(
						self._get_user_block_count(user_id)
					)
				)
				req_block_task = self._block_user(
					user_id,
					reason=(
						f'Exceeded daily agent input token limit, '
						f'blocked for {duration // 3600} hours'
					),
					duration_seconds=duration,
				)

			if rl_block_task and not req_block_task:
				db_write_back_tasks.append(rl_block_task)
				block = rl_block_task.blocked_entity
			elif req_block_task:
				db_write_back_tasks.append(req_block_task)
				block = req_block_task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def add_at_generation(
		self, user_id: str
	) -> BlockedEntity | None:
		"""
		Increments the count of access token generations for the given
		user and blocks the user if it exceeds the defined threshold
		for daily access token generations.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id not in self._user_stats:
				self._user_stats[user_id] = UserUsageStats(
					user_id=user_id, day_key=get_utc_day_key()
				)
			stats = self._user_stats[user_id]
			stats.access_tokens_generated_today += 1

			# Mark update
			self._add_user_to_update(user_id)

			# Check if user exceeds daily access token generation
			# limit
			if (
				stats.access_tokens_generated_today
				> MAX_DAILY_AT_GENERATED_PER_USER
			):
				duration = self._resolve_user_block_duration(
					self._get_user_block_count(user_id)
				)

				task = self._block_user(
					user_id,
					reason=(
						f'Exceeded daily access token generation '
						f'limit, blocked for {duration // 3600} hours'
					),
					duration_seconds=duration,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def add_claim_cookie_generation(
		self, user_id: str
	) -> BlockedEntity | None:
		"""
		Increments the count of claim cookie generations for the given
		user and blocks the user if it exceeds the defined threshold
		for daily claim cookie generations.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_user_if_new_day(user_id)
			if task:
				db_write_back_tasks.append(task)

			if user_id not in self._user_stats:
				self._user_stats[user_id] = UserUsageStats(
					user_id=user_id, day_key=get_utc_day_key()
				)
			stats = self._user_stats[user_id]
			stats.claim_cookies_generated_today += 1

			# Mark update
			self._add_user_to_update(user_id)

			# Check if user exceeds daily claim cookie generation
			# limit
			if (
				stats.claim_cookies_generated_today
				> MAX_DAILY_CLAIM_COOKIES_PER_USER
			):
				duration = self._resolve_user_block_duration(
					self._get_user_block_count(user_id)
				)

				task = self._block_user(
					user_id,
					reason=(
						f'Exceeded daily claim cookie generation '
						f'limit, blocked for {duration // 3600} hours'
					),
					duration_seconds=duration,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	# --- Cleanup and maintenance methods ---

	async def _delete_user_stats_from_db(
		self, user_ids: list[str]
	) -> None:
		"""
		Deletes the user's stats from the database, which can be used
		for cleanup purposes or to reset a user's history in cases of
		false positives or upon user request.
		"""
		batch_size = self._deletion_batch_size
		try:
			usage_stats_collection = await get_collection(
				MongoDBCollection.USER_USAGE_STATS
			)
			for i in range(0, len(user_ids), batch_size):
				batch_user_ids = user_ids[i : i + batch_size]
				await usage_stats_collection.delete_many(
					{'user_id': {'$in': batch_user_ids}}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_delete_user_stats',
				message='Failed to delete user stats from database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
				data={'user_ids': user_ids},
			)

	async def _delete_blocked_user_from_db(
		self, user_ids: list[str]
	) -> None:
		"""
		Deletes the blocked user record from the database, which can
		be used for cleanup purposes or to reset a user's history in
		cases of false positives or upon user request.
		"""
		batch_size = self._deletion_batch_size
		try:
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			for i in range(0, len(user_ids), batch_size):
				batch_user_ids = user_ids[i : i + batch_size]
				await blocked_entities_collection.delete_many(
					{'entity_id': {'$in': batch_user_ids}}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_delete_blocked_user',
				message='Failed to delete blocked user from database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
				data={'user_ids': user_ids},
			)

	async def _delete_user_data_state(
		self, user_ids: list[str]
	) -> None:
		"""
		Deletes all data related to the user, including usage stats
		and blocked user records, which can be used to comply with
		data deletion requests or to reset a user's history in cases
		of false positives.
		"""
		for user_id in user_ids:
			self._user_stats.pop(user_id, None)
			self._blocked_users.pop(user_id, None)
			self._rate_limit_tracker.pop(user_id, None)

	async def _periodic_cleanup(self) -> None:
		"""
		Periodically cleans up expired blocks and old stats from the
		database, which can be used to ensure that the system does not
		retain stale data and that blocks are lifted after their
		duration has passed.
		"""
		try:
			while True:
				cutoff_time = (
					get_timestamp_s() - self._persistence_time_s
				)
				expired_user_ids = []

				async with self._lock:
					for user_id, stats in self._user_stats.items():
						if (
							stats.last_blocked_at
							and stats.last_blocked_at < cutoff_time
						):
							expired_user_ids.append(user_id)

					if expired_user_ids:
						await self._delete_user_data_state(
							expired_user_ids
						)

				# Delete old records outside of lock
				if expired_user_ids:
					await self._delete_user_stats_from_db(
						expired_user_ids
					)
					await self._delete_blocked_user_from_db(
						expired_user_ids
					)

				await asyncio.sleep(self._cleanup_interval_seconds)
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='user_observer_cleanup',
				message='Error in periodic cleanup task',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)
