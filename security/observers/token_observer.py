"""
This module defines the token observer component for the Mwalika
Agent system, which is responsible for monitoring and enforcing
security policies related to token usage. The token observer tracks
usage statistics for access and refresh tokens, detects suspicious
behavior, and manages blocks on tokens based on observed patterns of
abuse or policy violations.
"""

import asyncio

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
from schemas.security.tokens import (
	AccessTokenUsageStats,
	RefreshTokenUsageStats,
	TokenType,
)
from security.config.observers import (
	ACCESS_TOKEN_BLOCK_DURATION,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2,
	AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3,
	FORGIVENESS_PERIOD_SECONDS,
	MAX_DAILY_AGENT_INPUT_TOKENS_PER_AT,
	MAX_DAILY_BAD_REQUESTS_PER_AT,
	MAX_DAILY_CLAIM_COOKIES_GENERATED_PER_AT,
	MAX_DAILY_REQUESTS_PER_AT,
	MAX_DAILY_REQUESTS_PER_RT,
	MAX_PER_MINUTE_REQUESTS_PER_AT,
	MAX_PER_MINUTE_REQUESTS_PER_RT,
	REFRESH_TOKEN_BLOCK_DURATION_LV_1,
	REFRESH_TOKEN_BLOCK_DURATION_LV_2,
	REFRESH_TOKEN_BLOCK_DURATION_LV_3,
)
from shared.time import get_timestamp_s, get_utc_day_key


class TokenObserver:
	"""
	The TokenObserver class is responsible for monitoring
	token usage stats for both access and refresh tokens,
	detecting suspicious behavior, and managing blocks on tokens
	based on observed patterns of abuse or policy violations.

	NOTE: Observer stats are not persisted to the database
	but are instead kept in-memory for fast access and updated
	as API requests are processed. Blocked entities are persisted
	to the database to ensure that blocks are enforced across
	restarts and can be shared across multiple instances of the
	system.
	"""

	def __init__(self):
		# Main state for tracking token usage stats,
		# keyed by token jit
		self._rt_usage_stats: dict[str, RefreshTokenUsageStats] = {}
		self._at_usage_stats: dict[str, AccessTokenUsageStats] = {}
		self._blocked_tokens: dict[str, BlockedEntity] = {}
		self._rate_limit_trackers: dict[str, MinuteCounter] = {}
		# Lock to ensure thread-safe access
		# to the observer's state
		self._lock = asyncio.Lock()
		self._db_write_back_task: asyncio.Task | None = None
		self._db_write_back_queue: asyncio.Queue[DbWriteBackTask] = (
			asyncio.Queue(maxsize=1_000)
		)
		# Used for cleanup
		self._cleanup_interval_seconds = 60  # 1 minute
		self._rt_persistence_time_s = (
			7 * 24 * 60 * 60
		)  # 7 days in seconds
		self._at_persistence_time_s = 30 * 60  # 30 minutes
		self._deletion_batch_size = 500
		self._cleanup_task: asyncio.Task | None = None

	# --- Observer lifecycle management ---

	async def start(self):
		"""
		Starts the token observer, by scheduling the
		background task for processing database write-backs.
		"""
		if self._db_write_back_task is None:
			self._db_write_back_task = asyncio.create_task(
				self._process_db_write_backs()
			)

		if self._cleanup_task is None:
			self._cleanup_task = asyncio.create_task(
				self._periodic_cleanup()
			)

		# Load currently blocked tokens from the database
		await self._load_blocked_tokens_from_db()

	async def stop(self):
		"""
		Stops the token observer, by cancelling the background task
		for processing database write-backs and performing any
		necessary cleanup.
		"""
		if self._db_write_back_task:
			self._db_write_back_task.cancel()
			try:
				await self._db_write_back_task
			except asyncio.CancelledError:
				pass

		if self._cleanup_task:
			self._cleanup_task.cancel()
			try:
				await self._cleanup_task
			except asyncio.CancelledError:
				pass

		self._db_write_back_task = None
		self._cleanup_task = None

	async def _load_blocked_tokens_from_db(self):
		"""
		Loads currently blocked tokens from the database into the
		observer's in-memory state, which allows the observer to
		enforce blocks across restarts and share block information
		across multiple instances of the system.
		"""
		try:
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			cursor = blocked_entities_collection.find(
				{
					'entity_type': {
						'$in': [
							BlockedEntityType.ACCESS_TOKEN,
							BlockedEntityType.REFRESH_TOKEN,
						]
					}
				}
			)
			async for doc in cursor:
				blocked_entity = BlockedEntity.model_validate(doc)
				self._blocked_tokens[blocked_entity.entity_id] = (
					blocked_entity
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='token_observer_db_load',
				message=(
					'Error loading blocked tokens from database on '
					'observer startup'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	# --- Database push management ---

	async def _process_db_write_backs(self):
		"""
		Continuously processes database write-back tasks from the
		queue, which are used to perform database operations related
		to blocking and unblocking tokens based on the defined
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
							await self._push_blocked_entity_to_db(
								blocked_entity=task.blocked_entity
							)
					elif (
						task.task_type
						== DbWriteBackTaskType.DELETE_BLOCKED_ENTITY
					):
						if task.blocked_entity:
							await self._delete_blocked_entity_from_db(
								blocked_entity=task.blocked_entity
							)
				except Exception as e:
					add_breadcrumb_capture_exception(
						category='token_observer_db_write_back',
						message=(
							'Error in processing DB write-back task'
						),
						cause=e,
						level=BreadcrumbLevel.ERROR,
					)
				finally:
					self._db_write_back_queue.task_done()
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='token_observer_db_write_back',
				message=(
					'Unexpected error in DB write-back '
					'background task'
				),
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
				category='token_observer_db_write_back_timeout',
				message=(
					'Database write-back queue timeout, '
					'failed to enqueue task'
				),
				cause=e,
				level=BreadcrumbLevel.WARNING,
			)

	# --- Blocking management ---

	def _get_token_block_count(
		self, token_id: str, token_type: TokenType
	) -> int:
		"""
		Retrieves the current block count for the given token ID from
		the in-memory state, which can be used to determine if a token
		should be blocked based on defined thresholds.
		"""
		if token_type == TokenType.ACCESS:
			stats = self._at_usage_stats.get(token_id)
		else:
			stats = self._rt_usage_stats.get(token_id)
		if stats:
			return stats.blocked_count
		return 0

	def _update_last_blocked_at(
		self, token_id: str, token_type: TokenType
	) -> None:
		"""
		Updates the last_blocked_at timestamp for the given token ID
		in the in-memory state, which can be used for tracking block
		durations and enforcing data retention policies.
		"""
		timestamp = get_timestamp_s()
		if token_type == TokenType.ACCESS:
			stats = self._at_usage_stats.get(token_id)
			if stats:
				stats.last_blocked_at = timestamp
		else:
			stats = self._rt_usage_stats.get(token_id)
			if stats:
				stats.last_blocked_at = timestamp

	def _block_rt(
		self, token_id: str, reason: str, duration_seconds: int
	) -> DbWriteBackTask:
		"""
		Blocks a refresh token by adding it to the in-memory state and
		creating a database write-back task to persist the block in
		the database, which ensures that the block is enforced across
		restarts and shared across multiple instances of the system.
		"""
		prev_block_count = self._get_token_block_count(
			token_id=token_id, token_type=TokenType.REFRESH
		)
		if token_id not in self._rt_usage_stats:
			self._rt_usage_stats[token_id] = RefreshTokenUsageStats(
				token_type=TokenType.REFRESH,
				token_jti=token_id,
				day_key=get_utc_day_key(),
			)
		self._rt_usage_stats[token_id].blocked_count = (
			prev_block_count + 1
		)
		self._update_last_blocked_at(
			token_id=token_id, token_type=TokenType.REFRESH
		)

		# If token is already blocked, keep longest block duration
		if token_id in self._blocked_tokens:
			existing_block = self._blocked_tokens[token_id]
			if existing_block.blocked_until > get_timestamp_s():
				# Update reason to reflect latest violation
				reason = f'{existing_block.reason}; {reason}'
				duration_seconds = max(
					existing_block.blocked_until - get_timestamp_s(),
					duration_seconds,
				)
		self._blocked_tokens[token_id] = BlockedEntity(
			entity_type=BlockedEntityType.REFRESH_TOKEN,
			entity_id=token_id,
			blocked_until=get_timestamp_s() + duration_seconds,
			reason=reason,
		)

		# Return database write-back task
		# to place in queue outside of lock
		return DbWriteBackTask(
			task_type=DbWriteBackTaskType.PUSH_BLOCKED_ENTITY,
			blocked_entity=self._blocked_tokens[
				token_id
			].model_copy(),
		)

	def _block_at(
		self, token_id: str, reason: str, duration_seconds: int
	) -> DbWriteBackTask:
		"""
		Blocks an access token by adding it to the in-memory state and
		creating a database write-back task to persist the block in
		the database, which ensures that the block is enforced across
		restarts and shared across multiple instances of the system.
		"""
		prev_block_count = self._get_token_block_count(
			token_id=token_id, token_type=TokenType.ACCESS
		)
		if token_id not in self._at_usage_stats:
			self._at_usage_stats[token_id] = AccessTokenUsageStats(
				token_type=TokenType.ACCESS,
				token_jti=token_id,
				day_key=get_utc_day_key(),
			)
		self._at_usage_stats[token_id].blocked_count = (
			prev_block_count + 1
		)
		self._update_last_blocked_at(
			token_id=token_id, token_type=TokenType.ACCESS
		)

		# If token is already blocked, keep longest block duration
		if token_id in self._blocked_tokens:
			existing_block = self._blocked_tokens[token_id]
			if existing_block.blocked_until > get_timestamp_s():
				# Update reason to reflect latest violation
				reason = f'{existing_block.reason}; {reason}'
				duration_seconds = max(
					existing_block.blocked_until - get_timestamp_s(),
					duration_seconds,
				)
		self._blocked_tokens[token_id] = BlockedEntity(
			entity_type=BlockedEntityType.ACCESS_TOKEN,
			entity_id=token_id,
			blocked_until=get_timestamp_s() + duration_seconds,
			reason=reason,
		)

		# Return database write-back task
		# to place in queue outside of lock
		return DbWriteBackTask(
			task_type=DbWriteBackTaskType.PUSH_BLOCKED_ENTITY,
			blocked_entity=self._blocked_tokens[
				token_id
			].model_copy(),
		)

	async def _push_blocked_entity_to_db(
		self, blocked_entity: BlockedEntity
	):
		"""
		Pushes a blocked entity record to the database, which can be
		used to persist blocks on tokens and ensure that they are
		enforced across restarts and shared across multiple instances
		of the system.
		"""
		try:
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
				category='token_observer_db_write_back',
				message=('Error pushing blocked entity to database'),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _delete_blocked_entity_from_db(
		self, blocked_entity: BlockedEntity
	):
		"""
		Deletes a blocked entity record from the database, which can
		be used for unblocking tokens and ensuring that blocks are
		removed across restarts and shared across multiple instances
		of the system.
		"""
		try:
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			await blocked_entities_collection.delete_one(
				{
					'entity_id': blocked_entity.entity_id,
					'entity_type': blocked_entity.entity_type,
				}
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='token_observer_db_write_back',
				message=(
					'Error deleting blocked entity from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	def _reset_and_unblock_token_if_new_day(
		self, token_id: str, token_type: TokenType
	) -> DbWriteBackTask | None:
		"""
		Performs reset for a token if a new day has started and
		unblocks the token if its block has expired.
		"""
		self._reset_token_block_count_if_new_day(
			token_id=token_id, token_type=token_type
		)
		return self._unblock_token_if_block_expired(token_id=token_id)

	def _unblock_token_if_block_expired(
		self, token_id: str
	) -> DbWriteBackTask | None:
		if token_id in self._blocked_tokens:
			blocked_entity = self._blocked_tokens[
				token_id
			].model_copy()
			if get_timestamp_s() > blocked_entity.blocked_until:
				del self._blocked_tokens[token_id]

				return DbWriteBackTask(
					task_type=DbWriteBackTaskType.DELETE_BLOCKED_ENTITY,
					blocked_entity=blocked_entity,
				)

	def _reset_token_block_count_if_new_day(
		self, token_id: str, token_type: TokenType
	) -> None:
		current_day_key = get_utc_day_key()
		if token_type == TokenType.ACCESS:
			stats = self._at_usage_stats.get(token_id)
			if stats and stats.day_key != current_day_key:
				stats.bad_requests_today = 0
				stats.agent_input_tokens_today = 0
				stats.claim_cookies_generated_today = 0
				stats.day_key = current_day_key

				# Reset block count if past forgiveness
				# window
				if stats.last_blocked_at:
					time_since_last_block = (
						get_timestamp_s() - stats.last_blocked_at
					)
					if (
						time_since_last_block
						> FORGIVENESS_PERIOD_SECONDS
					):
						stats.blocked_count = 0
		else:
			stats = self._rt_usage_stats.get(token_id)
			if stats and stats.day_key != current_day_key:
				stats.access_tokens_generated_today = 0
				stats.day_key = current_day_key

				# Reset block count if past forgiveness
				# window
				if stats.last_blocked_at:
					time_since_last_block = (
						get_timestamp_s() - stats.last_blocked_at
					)
					if (
						time_since_last_block
						> FORGIVENESS_PERIOD_SECONDS
					):
						stats.blocked_count = 0

	def _resolve_rt_block_duration(self, block_count: int) -> int:
		if block_count == 0:
			return REFRESH_TOKEN_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return REFRESH_TOKEN_BLOCK_DURATION_LV_2
		else:
			return REFRESH_TOKEN_BLOCK_DURATION_LV_3

	def _resolve_agent_input_token_block_duration(
		self, block_count: int
	) -> int:
		if block_count == 0:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_1
		elif block_count == 1:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_2
		else:
			return AGENT_INPUT_TOKEN_BLOCK_DURATION_LV_3

	# --- Token status inspection ---

	async def is_token_blocked(
		self, token_id: str, token_type: TokenType
	) -> BlockedEntity | None:
		"""
		Checks if the given token ID is
		currently blocked
		"""
		db_write_back_tasks = []
		async with self._lock:
			task = self._reset_and_unblock_token_if_new_day(
				token_id=token_id, token_type=token_type
			)
			if task:
				db_write_back_tasks.append(task)

			result = self._blocked_tokens.get(token_id)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)
		return result

	def _increment_and_check_rate_limit(
		self,
		token_id: str,
		token_type: TokenType,
	) -> DbWriteBackTask | None:
		"""
		Increments the per-minute request count for the given token ID
		and checks if it exceeds defined rate limits, returning a
		database write-back task to block the token if limits are
		exceeded.
		"""
		current_time_s = get_timestamp_s()
		min_key = current_time_s - (current_time_s % 60)

		if token_id not in self._rate_limit_trackers:
			self._rate_limit_trackers[token_id] = MinuteCounter(
				minute_key=min_key, count=1
			)
		else:
			tracker = self._rate_limit_trackers[token_id]
			if tracker.minute_key == min_key:
				tracker.count += 1
			else:
				tracker.minute_key = min_key
				tracker.count = 1

		# If token exceeds per-minute limit,
		# block it and return DB write-back task
		limit = (
			MAX_PER_MINUTE_REQUESTS_PER_RT
			if token_type == TokenType.REFRESH
			else MAX_PER_MINUTE_REQUESTS_PER_AT
		)
		block_count = self._get_token_block_count(
			token_id=token_id, token_type=token_type
		)

		if token_type == TokenType.REFRESH:
			duration = self._resolve_rt_block_duration(block_count)
		else:
			duration = ACCESS_TOKEN_BLOCK_DURATION

		if self._rate_limit_trackers[token_id].count > limit:
			reason = (
				f'Exceeded per-minute request limit of {limit} for '
				f'{token_type.value} token. Blocked for '
				f'{duration // 60} minutes.'
			)
			if token_type == TokenType.REFRESH:
				return self._block_rt(
					token_id=token_id,
					reason=reason,
					duration_seconds=duration,
				)
			else:
				return self._block_at(
					token_id=token_id,
					reason=reason,
					duration_seconds=duration,
				)

	# --- Refresh token specific management ---

	async def update_latest_rt_usage(
		self,
		token_id: str,
	) -> None:
		"""
		Updates the latest usage information for a refresh token,
		which can be used for enforcing rate limits and tracking usage
		patterns for security monitoring and analytics purposes.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_token_if_new_day(
				token_id=token_id, token_type=TokenType.REFRESH
			)
			if task:
				db_write_back_tasks.append(task)

			# Mark usage
			if token_id not in self._rt_usage_stats:
				self._rt_usage_stats[token_id] = (
					RefreshTokenUsageStats(
						token_type=TokenType.REFRESH,
						token_jti=token_id,
						day_key=get_utc_day_key(),
					)
				)
			stats = self._rt_usage_stats[token_id]
			stats.requests_today += 1
			stats.last_api_request_at = get_timestamp_s()

			# Check per-minute rate limit
			rl_block_task = self._increment_and_check_rate_limit(
				token_id=token_id, token_type=TokenType.REFRESH
			)
			req_block_task = None

			# If user exceeds daily request limit, block
			# and create DB write-back task
			if stats.requests_today > MAX_DAILY_REQUESTS_PER_RT:
				duration = self._resolve_rt_block_duration(
					self._get_token_block_count(
						token_id=token_id,
						token_type=TokenType.REFRESH,
					)
				)
				req_block_task = self._block_rt(
					token_id=token_id,
					reason=(
						f'Exceeded daily request limit for refresh '
						f'token. Blocked for {duration // 60} '
						f'minutes.'
					),
					duration_seconds=duration,
				)
			if rl_block_task and not req_block_task:
				db_write_back_tasks.append(rl_block_task)
			elif req_block_task:
				db_write_back_tasks.append(req_block_task)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	# --- Access token specific management ---

	async def update_latest_at_usage(
		self,
		token_id: str,
	) -> None:
		"""
		Updates the latest usage information for an access token,
		which can be used for enforcing rate limits and tracking usage
		patterns for security monitoring and analytics purposes.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_token_if_new_day(
				token_id=token_id, token_type=TokenType.ACCESS
			)
			if task:
				db_write_back_tasks.append(task)

			# Mark usage
			if token_id not in self._at_usage_stats:
				self._at_usage_stats[token_id] = (
					AccessTokenUsageStats(
						token_type=TokenType.ACCESS,
						token_jti=token_id,
						day_key=get_utc_day_key(),
					)
				)
			stats = self._at_usage_stats[token_id]
			stats.requests_today += 1
			stats.last_api_request_at = get_timestamp_s()

			# Check per-minute rate limit
			rl_block_task = self._increment_and_check_rate_limit(
				token_id=token_id, token_type=TokenType.ACCESS
			)
			req_block_task = None

			# If user exceeds daily request limit, block
			# and create DB write-back task
			if stats.requests_today > MAX_DAILY_REQUESTS_PER_AT:
				req_block_task = self._block_at(
					token_id=token_id,
					reason=(
						f'Exceeded daily request limit for access '
						f'token. Blocked for '
						f'{ACCESS_TOKEN_BLOCK_DURATION // 60} '
						f'minutes.'
					),
					duration_seconds=ACCESS_TOKEN_BLOCK_DURATION,
				)
			if rl_block_task and not req_block_task:
				db_write_back_tasks.append(rl_block_task)
			elif req_block_task:
				db_write_back_tasks.append(req_block_task)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	async def add_at_bad_request(
		self,
		token_id: str,
	) -> None:
		"""
		Increments the bad request count for an access token, which
		can be used for enforcing rate limits and tracking usage
		patterns for security monitoring and analytics purposes.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_token_if_new_day(
				token_id=token_id, token_type=TokenType.ACCESS
			)
			if task:
				db_write_back_tasks.append(task)

			if token_id not in self._at_usage_stats:
				self._at_usage_stats[token_id] = (
					AccessTokenUsageStats(
						token_type=TokenType.ACCESS,
						token_jti=token_id,
						day_key=get_utc_day_key(),
					)
				)
			stats = self._at_usage_stats[token_id]
			stats.bad_requests_today += 1

			# If user exceeds daily bad request limit, block
			# and create DB write-back task
			if (
				stats.bad_requests_today
				> MAX_DAILY_BAD_REQUESTS_PER_AT
			):
				req_block_task = self._block_at(
					token_id=token_id,
					reason=(
						f'Exceeded daily bad request limit for '
						f'access token. Blocked for '
						f'{ACCESS_TOKEN_BLOCK_DURATION // 60} '
						f'minutes.'
					),
					duration_seconds=ACCESS_TOKEN_BLOCK_DURATION,
				)
				db_write_back_tasks.append(req_block_task)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	async def add_at_claim_cookie_generated(
		self,
		token_id: str,
	) -> None:
		"""
		Increments the claim cookie generated count for an access,
		token, which can be used for enforcing rate limits and
		tracking usage patterns for security monitoring and analytics
		purposes.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_token_if_new_day(
				token_id=token_id, token_type=TokenType.ACCESS
			)
			if task:
				db_write_back_tasks.append(task)

			if token_id not in self._at_usage_stats:
				self._at_usage_stats[token_id] = (
					AccessTokenUsageStats(
						token_type=TokenType.ACCESS,
						token_jti=token_id,
						day_key=get_utc_day_key(),
					)
				)
			stats = self._at_usage_stats[token_id]
			stats.claim_cookies_generated_today += 1

			# If user exceeds daily claim cookie generation limit,
			# block and create DB write-back task
			if (
				stats.claim_cookies_generated_today
				> MAX_DAILY_CLAIM_COOKIES_GENERATED_PER_AT
			):
				task = self._block_at(
					token_id=token_id,
					reason=(
						f'Exceeded daily claim cookie generation '
						f'limit for access token. Blocked for '
						f'{ACCESS_TOKEN_BLOCK_DURATION // 60} '
						f'minutes.'
					),
					duration_seconds=ACCESS_TOKEN_BLOCK_DURATION,
				)
				db_write_back_tasks.append(task)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	async def add_at_agent_input_tokens(
		self,
		token_id: str,
		token_count: int,
	) -> None:
		"""
		Increments the agent input token count for an access token,
		which can be used for enforcing rate limits and tracking
		usage patterns for security monitoring and analytics purposes.
		"""
		db_write_back_tasks = []
		async with self._lock:
			# Perform resets
			task = self._reset_and_unblock_token_if_new_day(
				token_id=token_id, token_type=TokenType.ACCESS
			)
			if task:
				db_write_back_tasks.append(task)

			if token_id not in self._at_usage_stats:
				self._at_usage_stats[token_id] = (
					AccessTokenUsageStats(
						token_type=TokenType.ACCESS,
						token_jti=token_id,
						day_key=get_utc_day_key(),
					)
				)
			stats = self._at_usage_stats[token_id]
			stats.agent_input_tokens_today += max(token_count, 0)

			# Check if token exceeds rate limit
			rl_block_task = self._increment_and_check_rate_limit(
				token_id=token_id, token_type=TokenType.ACCESS
			)
			req_block_task = None

			# If user exceeds daily agent input token limit, block
			# and create DB write-back task
			if (
				stats.agent_input_tokens_today
				> MAX_DAILY_AGENT_INPUT_TOKENS_PER_AT
			):
				duration = (
					self._resolve_agent_input_token_block_duration(
						self._get_token_block_count(
							token_id=token_id,
							token_type=TokenType.ACCESS,
						)
					)
				)
				req_block_task = self._block_at(
					token_id=token_id,
					reason=(
						f'Exceeded daily agent input token limit for '
						f'access token. Blocked for {duration // 60} '
						f'minutes.'
					),
					duration_seconds=duration,
				)
			if rl_block_task and not req_block_task:
				db_write_back_tasks.append(rl_block_task)
			elif req_block_task:
				db_write_back_tasks.append(req_block_task)

		# Place database write-back tasks in queue outside lock
		await self._wait_for_db_task_queue(db_write_back_tasks)

	# --- Cleanup and maintenance methods ---

	async def _delete_token_block_records_from_db(
		self, token_ids: list[str], token_type: TokenType
	) -> None:
		"""
		Deletes all block records for a given token ID and type from
		the database, which can be used for cleanup and maintenance
		purposes.
		"""
		if not token_ids:
			return
		entity_type = (
			BlockedEntityType.ACCESS_TOKEN
			if token_type == TokenType.ACCESS
			else BlockedEntityType.REFRESH_TOKEN
		)
		batch_size = self._deletion_batch_size
		try:
			blocked_entities_collection = await get_collection(
				MongoDBCollection.BLOCKED_ENTITIES
			)
			for i in range(0, len(token_ids), batch_size):
				batch_token_ids = token_ids[i : i + batch_size]
				await blocked_entities_collection.delete_many(
					{
						'entity_id': {'$in': batch_token_ids},
						'entity_type': entity_type,
					}
				)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='token_observer_db_cleanup',
				message=(
					'Error deleting token block records from database'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)

	async def _delete_rt_data_state(
		self, token_ids: list[str]
	) -> None:
		"""
		Deletes all data related to the given refresh token IDs from
		the observer's in-memory state and the database, which can be
		used for cleanup when refresh tokens are revoked or rotated.
		"""
		for token_id in token_ids:
			# Remove from in-memory state
			self._rt_usage_stats.pop(token_id, None)
			self._rate_limit_trackers.pop(token_id, None)
			self._blocked_tokens.pop(token_id, None)

	async def _delete_at_data_state(
		self, token_ids: list[str]
	) -> None:
		"""
		Deletes all data related to the given access token IDs from
		the observer's in-memory state and the database, which can be
		used for cleanup when access tokens are revoked or rotated.
		"""
		for token_id in token_ids:
			# Remove from in-memory state
			self._at_usage_stats.pop(token_id, None)
			self._rate_limit_trackers.pop(token_id, None)
			self._blocked_tokens.pop(token_id, None)

	async def _rt_cleanup(self):
		cutoff_time = get_timestamp_s() - self._rt_persistence_time_s
		rt_ids_to_cleanup = []

		async with self._lock:
			for token_id, stats in self._rt_usage_stats.items():
				if (
					stats.last_api_request_at
					and stats.last_api_request_at < cutoff_time
				):
					rt_ids_to_cleanup.append(token_id)

			if rt_ids_to_cleanup:
				await self._delete_rt_data_state(rt_ids_to_cleanup)

		# Delete old records from database outside of lock
		if rt_ids_to_cleanup:
			await self._delete_token_block_records_from_db(
				token_ids=rt_ids_to_cleanup,
				token_type=TokenType.REFRESH,
			)

	async def _at_cleanup(self):
		cutoff_time = get_timestamp_s() - self._at_persistence_time_s
		at_ids_to_cleanup = []

		async with self._lock:
			for token_id, stats in self._at_usage_stats.items():
				if (
					stats.last_api_request_at
					and stats.last_api_request_at < cutoff_time
				):
					at_ids_to_cleanup.append(token_id)

			if at_ids_to_cleanup:
				await self._delete_at_data_state(at_ids_to_cleanup)

		# Delete old records from database outside of lock
		if at_ids_to_cleanup:
			await self._delete_token_block_records_from_db(
				token_ids=at_ids_to_cleanup,
				token_type=TokenType.ACCESS,
			)

	async def _periodic_cleanup(self):
		"""
		Periodically performs cleanup tasks such as removing expired
		blocks from the in-memory state and database, which helps to
		ensure that the observer's state remains manageable and that
		blocks are not enforced longer than necessary.
		"""
		try:
			while True:
				await self._rt_cleanup()
				await self._at_cleanup()
				await asyncio.sleep(self._cleanup_interval_seconds)
		except asyncio.CancelledError:
			pass
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='token_observer_periodic_cleanup',
				message=(
					'Unexpected error in periodic cleanup '
					'background task'
				),
				cause=e,
				level=BreadcrumbLevel.ERROR,
			)
