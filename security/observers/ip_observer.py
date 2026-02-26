"""
This module defines the ip observer component of the
Mwalika Agent system, which is responsible for monitoring
and managing IP address usage statistics, enforcing blocks,
and maintaining security policies related to IP addresses.
"""

import asyncio

from pymongo import UpdateOne

from databases.mongodb.main import MongoDBCollection, get_collection
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb_capture_exception,
)
from schemas.security.ips import IpUsageStats
from schemas.security.observers import (
	BlockedEntity,
	BlockedEntityType,
	DbWriteBackTask,
	DbWriteBackTaskType,
	MinuteCounter,
)
from security.config.observers import (
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3,
	FORGIVENESS_PERIOD_SECONDS,
	HOURS_IN_SECONDS_24,
	IP_BLOCK_DURATION_LV_1,
	IP_BLOCK_DURATION_LV_2,
	IP_BLOCK_DURATION_LV_3,
	MAX_DAILY_AGENT_INPUT_TOKENS_PER_IP,
	MAX_DAILY_BAD_REQUESTS_PER_IP,
	MAX_DAILY_CLAIM_COOKIES_PER_IP,
	MAX_DAILY_REFRESH_TOKENS_PER_IP,
	MAX_DAILY_REQUESTS_PER_IP,
	MAX_PER_MINUTE_REQUESTS_PER_IP,
	MAX_WS_CONNECTIONS_PER_IP,
	WS_BLOCK_DURATION_LV_1,
	WS_BLOCK_DURATION_LV_2,
	WS_BLOCK_DURATION_LV_3,
)
from shared.time import get_timestamp_s, get_utc_day_key


class IpObserver:
	"""
	Observes and manages IP address usage
	statistics, blocks, and security policies in
	the Mwalika Agent system.
	"""

	def __init__(self):
		# Main state for tracking IP usage
		self._ip_usage_stats: dict[str, IpUsageStats] = {}
		self._blocked_ips: dict[str, BlockedEntity] = {}
		self._rate_limit_tracker: dict[str, MinuteCounter] = {}
		# Lock to ensure thread-safe access to shared state
		self._lock = asyncio.Lock()
		# Used for periodic pushes of usage stats
		# to the database
		self._ips_to_update: set[str] = set()
		self._update_interval_seconds = 60
		self._max_size_to_force_push = 50
		self._last_update_time = get_timestamp_s()
		self._push_stats_task: asyncio.Task | None = None
		self._db_write_back_task: asyncio.Task | None = None
		self._db_write_back_queue: asyncio.Queue[DbWriteBackTask] = (
			asyncio.Queue(maxsize=1_000)
		)
		# Used for cleanup
		self._cleanup_interval_seconds = 60 * 60  # 1 hour
		self._retention_time_s = 7 * 24 * 60 * 60  # 7 days in seconds
		self._deletion_batch_size = 100
		self._cleanup_task: asyncio.Task | None = None

	# --- Observer lifecycle management ---

	async def start(self):
		"""
		Starts the IP observer by scheduling the periodic task
		to push usage stats to the database.
		"""
		if self._push_stats_task is None:
			self._push_stats_task = asyncio.create_task(
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

		# Load currently blocked IPs from the database
		await self._load_blocked_ips_from_db()

	async def stop(self):
		"""
		Stops the IP observer by canceling the scheduled task
		for pushing usage stats to the database.
		"""
		if self._push_stats_task is not None:
			self._push_stats_task.cancel()
			try:
				await self._push_stats_task
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

		self._push_stats_task = None
		self._db_write_back_task = None
		self._cleanup_task = None

	async def _load_blocked_ips_from_db(self):
		"""
		Loads currently blocked IP addresses from the database
		and populates the in-memory state for blocked IPs.
		"""
		try:
			blocked_entities_collection = get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			cursor = blocked_entities_collection.find(
				{'entity_type': BlockedEntityType.IP}
			)
			async for doc in cursor:
				blocked_entity = BlockedEntity.model_validate(doc)
				self._blocked_ips[blocked_entity.entity_id] = (
					blocked_entity
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_load_blocked_ips',
				message='Failed to load blocked IPs from database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)
			raise e

	# --- Database push management ---

	def _add_ip_to_update(self, ip_address: str):
		"""
		Adds an IP address to the set of IPs that need to have their
		usage stats updated in the database.
		"""
		self._ips_to_update.add(ip_address)

	async def _push_stats_to_db(self):
		"""
		Pushes the usage stats for IP addresses in the update set to
		the database and clears the update set.
		"""
		async with self._lock:
			if not self._ips_to_update:
				return

			ips_to_update = list(self._ips_to_update)
			ip_stats_snapshot = {
				ip: self._ip_usage_stats.get(ip)
				for ip in ips_to_update
				if ip in self._ip_usage_stats
			}
			self._ips_to_update.clear()

		try:
			ip_usage_collection = get_collection(
				MongoDBCollection.IP_USAGE_STATS
			)
			bulk_ops = []
			for ip_address in ip_stats_snapshot:
				stats = ip_stats_snapshot[ip_address]
				if stats:
					bulk_ops.append(
						UpdateOne(
							filter={'ip_address': ip_address},
							update={
								'$set': stats.model_dump(mode='json')
							},
							upsert=True,
						)
					)
			if bulk_ops:
				await ip_usage_collection.bulk_write(bulk_ops)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_push_stats',
				message='Failed to push IP usage stats to database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

			# If push fails re-add IPs to update set to
			# try again on next interval
			async with self._lock:
				self._ips_to_update.update(ips_to_update)

	async def _periodic_stats_push(self):
		"""
		Periodically pushes usage stats for IP addresses to
		the database at a defined interval or when the number of
		IPs to update exceeds a certain threshold.
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
					or len(self._ips_to_update)
					>= self._max_size_to_force_push
				):
					await self._push_stats_to_db()
					self._last_update_time = current_time
				await asyncio.sleep(1)
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_periodic_push',
				message='Error in periodic stats push loop',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _process_db_write_back_tasks(self):
		"""
		Continuously processes database write-back tasks from the
		queue, which are used to perform database operations related
		to blocking and unblocking IP addresses based on the defined
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
							await self._push_blocked_ip_to_db(
								task.blocked_entity
							)
					elif (
						task.task_type
						== DbWriteBackTaskType.DELETE_BLOCKED_ENTITY
					):
						if task.blocked_entity:
							await self._remove_blocked_ip_from_db(
								task.blocked_entity.entity_id
							)
				except Exception as e:
					blocked_entity = (
						task.blocked_entity.model_dump()
						if task.blocked_entity
						else None
					)
					add_breadcrumb_capture_exception(
						category='ip_observer_db_write_back',
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
				category='ip_observer_db_write_back',
				message='Error in processing DB write-back tasks',
				cause=e,
				level=BreadcrumbLevel.ERROR,
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

	async def _push_blocked_ip_to_db(
		self, blocked_entity: BlockedEntity
	):
		"""
		Pushes a newly blocked IP address to the database to ensure
		that the block is persisted and can be enforced across all
		instances of the application.
		"""
		try:
			# Push to database
			blocked_entities_collection = get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			await blocked_entities_collection.update_one(
				{
					'entity_type': blocked_entity.entity_type,
					'entity_id': blocked_entity.entity_id,
				},
				{'$set': blocked_entity.model_dump(mode='json')},
				upsert=True,
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_push_blocked_ip',
				message='Failed to push blocked IP to database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _remove_blocked_ip_from_db(self, ip_address: str):
		"""
		Removes a blocked IP address from the database when it is
		unblocked, which can be used to clean up block records and
		ensure that the IP is treated as unblocked in future checks.
		"""
		try:
			blocked_entities_collection = get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			await blocked_entities_collection.delete_one(
				{
					'entity_type': BlockedEntityType.IP,
					'entity_id': ip_address,
				}
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_remove_blocked_ip',
				message='Failed to remove blocked IP from database',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	# --- Blocking management ---

	def _get_ip_block_count(self, ip_address: str) -> int:
		"""
		Retrieves the current block count for the given IP address,
		which can be used to determine the severity level of a block.
		"""
		if ip_address in self._ip_usage_stats:
			return self._ip_usage_stats[ip_address].blocked_count
		return 0

	def _update_last_blocked_at(self, ip_address: str):
		"""
		Updates the last_blocked_at timestamp for the given IP address
		in the usage stats, which can be used to track block durations
		and manage data retention policies.
		"""
		if ip_address in self._ip_usage_stats:
			self._ip_usage_stats[
				ip_address
			].last_blocked_at = get_timestamp_s()

	def _block_ip(
		self, ip_address: str, reason: str, duration_seconds: int
	) -> DbWriteBackTask:
		"""
		Blocks the given IP address for a specified duration by
		creating a BlockedEntity and pushing it to the database, and
		updates the in-memory state to reflect the block.
		"""
		prev_block_count = self._get_ip_block_count(ip_address)
		if ip_address not in self._ip_usage_stats:
			self._ip_usage_stats[ip_address] = IpUsageStats(
				ip_address=ip_address,
				day_key=get_utc_day_key(),
			)
		self._ip_usage_stats[ip_address].blocked_count = (
			prev_block_count + 1
		)
		self._update_last_blocked_at(ip_address)

		# If IP is already blocked, keep longest block duration and
		# update reason to reflect latest violation
		if ip_address in self._blocked_ips:
			existing_block = self._blocked_ips[ip_address]
			if existing_block.blocked_until > get_timestamp_s():
				reason = f'{existing_block.reason}; {reason}'
				duration_seconds = max(
					duration_seconds,
					existing_block.blocked_until - get_timestamp_s(),
				)

		self._blocked_ips[ip_address] = BlockedEntity(
			entity_type=BlockedEntityType.IP,
			entity_id=ip_address,
			reason=reason,
			blocked_until=get_timestamp_s() + duration_seconds,
		)

		# Return database write-back to place
		# in queue outside lock
		return DbWriteBackTask(
			task_type=DbWriteBackTaskType.PUSH_BLOCKED_ENTITY,
			blocked_entity=self._blocked_ips[ip_address].model_copy(),
		)

	def _reset_and_unblock_ip_if_new_day(
		self, ip_address: str
	) -> DbWriteBackTask | None:
		"""
		Performs reset for ip if new day and checks if
		block has expired, if so unblocks the IP by removing it from
		the in-memory state and database.
		"""
		self._reset_ip_stats_if_new_day(ip_address)
		return self._unblock_ip_if_block_expired(ip_address)

	def _unblock_ip_if_block_expired(
		self, ip_address: str
	) -> DbWriteBackTask | None:
		"""
		Unblocks the given IP address if the block duration has
		expired by removing it from the in-memory state and allowing
		it to be treated as unblocked in future checks.
		"""
		if ip_address in self._blocked_ips:
			blocked_entity = self._blocked_ips[
				ip_address
			].model_copy()
			if get_timestamp_s() >= blocked_entity.blocked_until:
				del self._blocked_ips[ip_address]

				# Return database write-back to place in
				# queue outside lock
				return DbWriteBackTask(
					task_type=DbWriteBackTaskType.DELETE_BLOCKED_ENTITY,
					blocked_entity=blocked_entity,
				)

	def _reset_ip_stats_if_new_day(self, ip_address: str):
		"""
		Resets the daily usage statistics for the given IP address if
		a new day has started, which can be used to enforce daily
		limits and maintain accurate usage tracking.
		"""
		current_day_key = get_utc_day_key()
		if (
			ip_address in self._ip_usage_stats
			and self._ip_usage_stats[ip_address].day_key
			!= current_day_key
		):
			stats = self._ip_usage_stats[ip_address]
			# Resets for new day
			stats.day_key = current_day_key
			stats.requests_today = 0
			stats.bad_requests_today = 0
			stats.agent_input_tokens_today = 0

			# Reset block count if last block was before
			# forgiveness period
			if stats.last_blocked_at:
				time_since_last_block = (
					get_timestamp_s() - stats.last_blocked_at
				)
				if (
					time_since_last_block
					>= FORGIVENESS_PERIOD_SECONDS
				):
					stats.blocked_count = 0

	def _resolve_ip_block_duration(self, block_count: int) -> int:
		"""
		Determines the block duration for an IP address based on the
		block count, which can be used to enforce escalating block
		durations for repeat offenders.
		"""
		if block_count == 0:
			return IP_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return IP_BLOCK_DURATION_LV_2
		else:
			return IP_BLOCK_DURATION_LV_3

	def _resolve_ws_block_duration(self, block_count: int) -> int:
		"""
		Determines the block duration for WebSocket connections based
		on the block count, which can be used to enforce escalating
		block durations for repeat offenders.
		"""
		if block_count == 0:
			return WS_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return WS_BLOCK_DURATION_LV_2
		else:
			return WS_BLOCK_DURATION_LV_3

	def _resolve_agent_input_token_block_duration(
		self, block_count: int
	) -> int:
		"""
		Determines the block duration for agent input token usage
		based on the block count, which can be used to enforce
		escalating block durations for repeat offenders.
		"""
		if block_count == 0:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2
		else:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3

	# --- IP status inspection ---

	async def is_ip_blocked(
		self, ip_address: str
	) -> BlockedEntity | None:
		"""
		Checks if the given IP address is currently blocked and
		returns the corresponding BlockedEntity if it is blocked,
		or None if it is not blocked.
		"""
		db_write_back_tasks = []
		async with self._lock:
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)
			result = self._blocked_ips.get(ip_address)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

		# Return block status result
		return result

	# --- Public status update methods ---

	def _increment_and_check_rate_limit(
		self, ip_address: str
	) -> DbWriteBackTask | None:
		"""
		Increments the request count for the given IP address and
		checks if it exceeds the defined per-minute or daily request
		limits blocking the IP address if necessary based on the
		configured thresholds and block durations.
		"""
		current_time_s = get_timestamp_s()
		min_key = current_time_s - (current_time_s % 60)

		if ip_address not in self._rate_limit_tracker:
			self._rate_limit_tracker[ip_address] = MinuteCounter(
				minute_key=min_key, count=1
			)
		else:
			tracker = self._rate_limit_tracker[ip_address]
			if tracker.minute_key == min_key:
				tracker.count += 1
			else:
				tracker.minute_key = min_key
				tracker.count = 1

		# If ip exceeds per-minute request limit, block them
		if (
			self._rate_limit_tracker[ip_address].count
			> MAX_PER_MINUTE_REQUESTS_PER_IP
		):
			duration = self._resolve_ip_block_duration(
				self._get_ip_block_count(ip_address)
			)

			return self._block_ip(
				ip_address=ip_address,
				reason=(
					f'Exceeded per-minute request limit, '
					f'blocked for {duration // 60} minutes'
				),
				duration_seconds=duration,
			)

	async def update_latest_request(
		self, ip_address: str
	) -> BlockedEntity | None:
		"""
		Updates the timestamp of the ip address's latest
		request and increments the daily request count.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			# Update stats
			if ip_address not in self._ip_usage_stats:
				self._ip_usage_stats[ip_address] = IpUsageStats(
					ip_address=ip_address,
					day_key=get_utc_day_key(),
				)

			stats = self._ip_usage_stats[ip_address]
			stats.requests_today += 1
			stats.last_api_request_at = get_timestamp_s()

			# Mark update
			self._add_ip_to_update(ip_address)

			# Check if IP exceeds per-minute request limit
			rl_block_task = self._increment_and_check_rate_limit(
				ip_address
			)
			req_block_task = None

			# If user exceeds daily request limit, block them
			if stats.requests_today > MAX_DAILY_REQUESTS_PER_IP:
				req_block_task = self._block_ip(
					ip_address=ip_address,
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
		self, ip_address: str
	) -> BlockedEntity | None:
		"""
		Increments the count of bad requests for the given IP address
		and blocks the IP if it exceeds the defined threshold for bad
		requests.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			# Update stats
			if ip_address not in self._ip_usage_stats:
				self._ip_usage_stats[ip_address] = IpUsageStats(
					ip_address=ip_address,
					day_key=get_utc_day_key(),
				)

			stats = self._ip_usage_stats[ip_address]
			stats.bad_requests_today += 1

			# Mark update
			self._add_ip_to_update(ip_address)

			# If user exceeds bad request limit, block them
			if (
				stats.bad_requests_today
				> MAX_DAILY_BAD_REQUESTS_PER_IP
			):
				task = self._block_ip(
					ip_address=ip_address,
					reason=(
						f'Exceeded daily bad request limit, '
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
		self, ip_address: str, connection_id: str
	) -> BlockedEntity | None:
		"""
		Adds a WebSocket connection ID to the list of active
		connections for the given IP address and blocks the IP
		if it exceeds the defined threshold for concurrent WebSocket
		connections.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			# Update stats
			if ip_address not in self._ip_usage_stats:
				self._ip_usage_stats[ip_address] = IpUsageStats(
					ip_address=ip_address,
					day_key=get_utc_day_key(),
				)

			stats = self._ip_usage_stats[ip_address]
			if connection_id not in stats.active_ws_connections:
				stats.active_ws_connections.append(connection_id)

			# Mark update
			self._add_ip_to_update(ip_address)

			# If user exceeds WebSocket connection limit, block them
			if (
				len(stats.active_ws_connections)
				> MAX_WS_CONNECTIONS_PER_IP
			):
				duration = self._resolve_ws_block_duration(
					self._get_ip_block_count(ip_address)
				)

				task = self._block_ip(
					ip_address=ip_address,
					reason=(
						f'Exceeded concurrent WebSocket connection '
						f'limit blocked for {duration // 60} '
						f'minutes'
					),
					duration_seconds=duration,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def remove_ws_connection(
		self, ip_address: str, connection_id: str
	):
		"""
		Removes a WebSocket connection ID from the list of active
		connections for the given IP address, which can be used to
		manage real-time interactions and enforce limits on concurrent
		connections.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Update stats
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			if ip_address in self._ip_usage_stats:
				stats = self._ip_usage_stats[ip_address]
				if connection_id in stats.active_ws_connections:
					stats.active_ws_connections.remove(connection_id)
					# Mark update
					self._add_ip_to_update(ip_address)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	async def add_agent_input_tokens(
		self, ip_address: str, token_count: int
	) -> BlockedEntity | None:
		"""
		Increments the count of agent input tokens for the given IP
		address and blocks the IP if it exceeds the defined threshold
		for daily agent input tokens.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			# Update stats
			if ip_address not in self._ip_usage_stats:
				self._ip_usage_stats[ip_address] = IpUsageStats(
					ip_address=ip_address,
					day_key=get_utc_day_key(),
				)

			stats = self._ip_usage_stats[ip_address]
			stats.agent_input_tokens_today += max(token_count, 0)

			# Mark update
			self._add_ip_to_update(ip_address)

			# Check if IP exceeds per-minute request limit
			rl_block_task = self._increment_and_check_rate_limit(
				ip_address
			)
			req_block_task = None

			# If user exceeds daily agent input token limit,
			# block them
			if (
				stats.agent_input_tokens_today
				> MAX_DAILY_AGENT_INPUT_TOKENS_PER_IP
			):
				duration = (
					self._resolve_agent_input_token_block_duration(
						self._get_ip_block_count(ip_address)
					)
				)

				req_block_task = self._block_ip(
					ip_address=ip_address,
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

	async def add_rt_generation(
		self, ip_address: str
	) -> BlockedEntity | None:
		"""
		Increments the count of refresh token generations for the
		given IP address and blocks the IP if it exceeds the defined
		threshold for daily refresh token generations.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			# Update stats
			if ip_address not in self._ip_usage_stats:
				self._ip_usage_stats[ip_address] = IpUsageStats(
					ip_address=ip_address,
					day_key=get_utc_day_key(),
				)

			stats = self._ip_usage_stats[ip_address]
			stats.refresh_tokens_generated_today += 1

			# Mark update
			self._add_ip_to_update(ip_address)

			# If user exceeds daily refresh token generation limit,
			# block them
			if (
				stats.refresh_tokens_generated_today
				> MAX_DAILY_REFRESH_TOKENS_PER_IP
			):
				duration = self._resolve_ip_block_duration(
					self._get_ip_block_count(ip_address)
				)

				task = self._block_ip(
					ip_address=ip_address,
					reason=(
						f'Exceeded daily refresh token generation '
						f'limit, blocked for '
						f'{duration // 3600} hours'
					),
					duration_seconds=duration,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	async def add_claim_cookie_generation(
		self, ip_address: str
	) -> BlockedEntity | None:
		"""
		Increments the count of claim cookie generations for the given
		IP address and blocks the IP if it exceeds the defined
		threshold for daily claim cookie generations.
		"""
		db_write_back_tasks = []
		block: BlockedEntity | None = None

		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_ip_if_new_day(ip_address)
			if task:
				db_write_back_tasks.append(task)

			# Update stats
			if ip_address not in self._ip_usage_stats:
				self._ip_usage_stats[ip_address] = IpUsageStats(
					ip_address=ip_address,
					day_key=get_utc_day_key(),
				)

			stats = self._ip_usage_stats[ip_address]
			stats.claim_cookies_generated_today += 1

			# Mark update
			self._add_ip_to_update(ip_address)

			# If user exceeds daily claim cookie generation limit,
			# block them
			if (
				stats.claim_cookies_generated_today
				> MAX_DAILY_CLAIM_COOKIES_PER_IP
			):
				duration = self._resolve_ip_block_duration(
					self._get_ip_block_count(ip_address)
				)

				task = self._block_ip(
					ip_address=ip_address,
					reason=(
						f'Exceeded daily claim cookie generation '
						f'limit, blocked for '
						f'{duration // 3600} hours'
					),
					duration_seconds=duration,
				)
				db_write_back_tasks.append(task)
				block = task.blocked_entity

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return block

	# --- Cleanup and maintenance methods ---

	async def _delete_ip_stats_from_db(self, ip_addresses: list[str]):
		"""
		Deletes the usage stats for the given IP addresses from the
		database, which can be used for cleanup of old records or
		in response to data retention policies.
		"""
		batch_size = self._deletion_batch_size
		try:
			ip_usage_collection = get_collection(
				MongoDBCollection.IP_USAGE_STATS
			)
			for i in range(0, len(ip_addresses), batch_size):
				batch = ip_addresses[i : i + batch_size]
				await ip_usage_collection.delete_many(
					{'ip_address': {'$in': batch}}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_delete_ip_stats',
				message=(
					'Failed to delete IP usage stats from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _delete_blocked_ips_from_db(
		self, ip_addresses: list[str]
	):
		"""
		Deletes the blocked IP record for the given IP addresses from
		the database, which can be used for cleanup of old records or
		in response to data retention policies.
		"""
		batch_size = self._deletion_batch_size
		try:
			blocked_entities_collection = get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			for i in range(0, len(ip_addresses), batch_size):
				batch = ip_addresses[i : i + batch_size]
				await blocked_entities_collection.delete_many(
					{
						'entity_type': BlockedEntityType.IP,
						'entity_id': {'$in': batch},
					}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_delete_blocked_ips',
				message=(
					'Failed to delete blocked IPs from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _delete_ip_data_state(self, ip_addresses: list[str]):
		"""
		Deletes all data related to the given IP addresses from the
		database and in-memory state, which can be used for cleanup or
		in response to data retention policies.
		"""
		for ip_address in ip_addresses:
			self._ip_usage_stats.pop(ip_address, None)
			self._blocked_ips.pop(ip_address, None)
			self._rate_limit_tracker.pop(ip_address, None)

	async def _periodic_cleanup(self):
		"""
		Periodically performs cleanup of old IP usage stats and
		blocked IP records from the database based on the defined
		persistence duration, which can help manage storage and
		ensure that old data does not accumulate indefinitely.
		"""
		try:
			while True:
				cutoff_time = (
					get_timestamp_s() - self._retention_time_s
				)
				ip_addresses_to_delete = []

				async with self._lock:
					for (
						ip_address,
						stats,
					) in self._ip_usage_stats.items():
						if (
							stats.last_api_request_at
							and stats.last_api_request_at
							< cutoff_time
							and ip_address not in self._blocked_ips
						):
							ip_addresses_to_delete.append(ip_address)

					if ip_addresses_to_delete:
						await self._delete_ip_data_state(
							ip_addresses_to_delete
						)

				# Delete old records outside of lock
				if ip_addresses_to_delete:
					await self._delete_ip_stats_from_db(
						ip_addresses_to_delete
					)
					await self._delete_blocked_ips_from_db(
						ip_addresses_to_delete
					)

				await asyncio.sleep(self._cleanup_interval_seconds)
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='ip_observer_periodic_cleanup',
				message='Error in periodic cleanup loop',
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)
