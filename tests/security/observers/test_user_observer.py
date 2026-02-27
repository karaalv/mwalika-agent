"""
This module contains tests for the UserObserver class
used as a security feature in the Mwalika Agent system.
The tests cover core functionality such as user blocking and
unblocking, as well as edge cases and error handling.
"""

from collections.abc import AsyncGenerator

import pytest

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.security.observers import (
	BlockedEntity,
	BlockedEntityType,
)
from schemas.security.users import UserUsageStats
from security.config.observers import MAX_PER_MINUTE_REQUESTS_PER_USER
from security.observers.user_observer import UserObserver
from shared.ids import generate_uuid_str

# --- Test fixtures ---


@pytest.fixture(scope='module')
async def user_observer() -> AsyncGenerator[UserObserver, None]:
	obs = UserObserver()

	# Make tests fast and deterministic.
	obs._cleanup_interval_seconds = 1
	obs._update_interval_seconds = 1

	await obs.start()
	yield obs
	await obs.stop()


@pytest.fixture(scope='module', autouse=True)
async def _cleanup_security_db():
	yield

	user_stats = get_collection(MongoDBCollection.USER_USAGE_STATS)
	blocks = get_collection(MongoDBCollection.BLOCKED_ENTITIES)

	await user_stats.delete_many({})
	await blocks.delete_many({'entity_type': BlockedEntityType.USER})


# --- Helper functions ---


async def _get_block_from_db(user_id: str) -> BlockedEntity | None:
	blocks = get_collection(MongoDBCollection.BLOCKED_ENTITIES)
	block_doc = await blocks.find_one(
		{
			'entity_type': BlockedEntityType.USER,
			'entity_id': user_id,
		},
		{'_id': 0},
	)
	if block_doc is not None:
		return BlockedEntity(**block_doc)
	return None


async def _get_user_stats_from_db(
	user_id: str,
) -> UserUsageStats | None:
	user_stats_collection = get_collection(
		MongoDBCollection.USER_USAGE_STATS
	)
	stats_doc = await user_stats_collection.find_one(
		{'user_id': user_id},
		{'_id': 0},
	)
	if stats_doc is not None:
		return UserUsageStats(**stats_doc)
	return None


# --- Test cases ---


async def test_update_latest_request(user_observer: UserObserver):
	user_id = generate_uuid_str()

	block = await user_observer.update_latest_request(user_id)
	assert block is None

	stats = user_observer._user_stats.get(user_id)
	assert stats is not None
	assert stats.requests_today == 1
	assert stats.last_api_request_at is not None


async def test_per_minute_rl_blocks(user_observer: UserObserver):
	user_id = generate_uuid_str()

	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_USER + 1):
		block = await user_observer.update_latest_request(user_id)

	assert block is not None
	assert block.entity_id == user_id
	assert block.entity_type == BlockedEntityType.USER


async def test_block_persists_to_db(user_observer: UserObserver):
	user_id = generate_uuid_str()

	# Simulate MAX_PER_MINUTE_REQUESTS_PER_USER requests
	# in a minute to trigger blocking
	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_USER + 1):
		block = await user_observer.update_latest_request(user_id)

	assert block is not None

	# Wait for async write-back
	await user_observer._db_write_back_queue.join()

	# Check if the block was persisted to the database
	block = await _get_block_from_db(user_id)
	assert block is not None
	assert block.entity_id == user_id
	assert block.entity_type == BlockedEntityType.USER


async def test_cleanup_removes_old_stats(user_observer: UserObserver):
	user_id = generate_uuid_str()

	# Update latest request to create stats
	await user_observer.update_latest_request(user_id)

	# Wait for async write-back
	await user_observer._db_write_back_queue.join()

	# Manually set last request time to be old
	stats = user_observer._user_stats.get(user_id)
	assert stats is not None
	stats.last_api_request_at = 0

	# Run cleanup
	await user_observer._cleanup()

	# Check if stats were removed from memory
	assert user_id not in user_observer._user_stats
	# Check if stats were removed from the database
	db_stats = await _get_user_stats_from_db(user_id)
	assert db_stats is None
