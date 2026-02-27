"""
This module contains tests for the TokenObserver class
used as a security feature in the Mwalika Agent system.
The tests cover core functionality such as token blocking and
unblocking, as well as edge cases and error handling.
"""

from collections.abc import AsyncGenerator

import pytest

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.security.observers import (
	BlockedEntity,
	BlockedEntityType,
)
from security.config.observers import (
	MAX_PER_MINUTE_REQUESTS_PER_AT,
	MAX_PER_MINUTE_REQUESTS_PER_RT,
)
from security.observers.token_observer import TokenObserver, TokenType
from shared.ids import generate_uuid_str

# --- Test fixtures ---


@pytest.fixture(scope='module')
async def token_observer() -> AsyncGenerator[TokenObserver, None]:
	obs = TokenObserver()

	# Make tests fast and deterministic.
	obs._cleanup_interval_seconds = 1

	await obs.start()
	yield obs
	await obs.stop()


@pytest.fixture(scope='module', autouse=True)
async def _cleanup_security_db():
	yield

	blocks = get_collection(MongoDBCollection.BLOCKED_ENTITIES)

	await blocks.delete_many(
		{
			'entity_type': {
				'$in': [
					BlockedEntityType.REFRESH_TOKEN,
					BlockedEntityType.ACCESS_TOKEN,
				]
			}
		}
	)


# --- Helper functions ---


async def _get_block_from_db(token_id: str) -> BlockedEntity | None:
	blocks = get_collection(MongoDBCollection.BLOCKED_ENTITIES)
	block_doc = await blocks.find_one(
		{
			'entity_type': {
				'$in': [
					BlockedEntityType.REFRESH_TOKEN,
					BlockedEntityType.ACCESS_TOKEN,
				]
			},
			'entity_id': token_id,
		},
		{'_id': 0},
	)

	if block_doc is None:
		return None

	return BlockedEntity.model_validate(block_doc)


# --- Test cases ---


async def test_update_latest_rt_usage(token_observer: TokenObserver):
	# Generate a unique token ID for testing.
	token_id = generate_uuid_str()

	# Update usage stats for the token.
	await token_observer.update_latest_rt_usage(token_id)

	# Check if the usage stats were updated
	stats = token_observer._rt_usage_stats.get(token_id)
	assert stats is not None
	assert stats.token_jti == token_id
	assert stats.last_api_request_at is not None


async def test_per_minute_rt_request_limit(
	token_observer: TokenObserver,
):
	# Generate a unique token ID for testing.
	token_id = generate_uuid_str()

	# Simulate multiple requests to trigger blocking.
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_RT + 1):
		await token_observer.update_latest_rt_usage(token_id)

		# Wait for async write-back to complete.
	await token_observer._db_write_back_queue.join()

	# Check if the token is blocked in the database.
	block = await _get_block_from_db(token_id)
	assert block is not None
	assert block.entity_type == BlockedEntityType.REFRESH_TOKEN
	assert block.entity_id == token_id


async def test_block_persists_to_db(token_observer: TokenObserver):
	token_id = generate_uuid_str()

	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_RT + 1):
		block = await token_observer.update_latest_rt_usage(token_id)

	assert block is not None

	# Wait for async write-back to complete.
	await token_observer._db_write_back_queue.join()

	block = await _get_block_from_db(token_id)
	assert block is not None
	assert block.entity_id == token_id
	assert block.entity_type == BlockedEntityType.REFRESH_TOKEN


async def test_expired_block_is_removed_at(
	token_observer: TokenObserver,
):
	token_id = generate_uuid_str()

	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_AT + 1):
		block = await token_observer.update_latest_at_usage(token_id)

	assert block is not None

	# Expire it in memory
	mem_block = token_observer._blocked_tokens[token_id]
	mem_block.blocked_until = 0

	res = await token_observer.is_token_blocked(
		token_id, TokenType.ACCESS
	)
	assert res is None

	await token_observer._db_write_back_queue.join()

	block = await _get_block_from_db(token_id)
	assert block is None


async def test_cleanup_removes_old_stats(
	token_observer: TokenObserver,
):
	token_id = generate_uuid_str()

	# Update usage stats to create an old entry.
	await token_observer.update_latest_rt_usage(token_id)

	# Manually set the last request time to be old.
	stats = token_observer._rt_usage_stats.get(token_id)
	assert stats is not None
	stats.last_api_request_at = 0

	# Run cleanup.
	await token_observer._cleanup()

	# Check that the old stats were removed.
	assert token_id not in token_observer._rt_usage_stats
