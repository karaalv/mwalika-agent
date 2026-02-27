"""
This module contains tests for the IpObserver class
used as a security feature in the Mwalika Agent system.
The tests cover core functionality such as IP blocking and unblocking,
as well as edge cases and error handling.
"""

from collections.abc import AsyncGenerator

import pytest

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.security.ips import IpUsageStats
from schemas.security.observers import (
	BlockedEntity,
	BlockedEntityType,
)
from security.config.observers import MAX_PER_MINUTE_REQUESTS_PER_IP
from security.observers.ip_observer import IpObserver
from tests.utils.generate_data import gen_test_ip

# --- Test fixtures ---


@pytest.fixture(scope='module')
async def ip_observer() -> AsyncGenerator[IpObserver, None]:
	obs = IpObserver()

	# Make tests fast and deterministic.
	obs._update_interval_seconds = 1
	obs._cleanup_interval_seconds = 1

	await obs.start()
	yield obs
	await obs.stop()


@pytest.fixture(scope='module', autouse=True)
async def _cleanup_security_db():
	yield

	ip_stats = get_collection(MongoDBCollection.IP_USAGE_STATS)
	blocks = get_collection(MongoDBCollection.BLOCKED_ENTITIES)

	await ip_stats.delete_many({})
	await blocks.delete_many({'entity_type': BlockedEntityType.IP})


# --- Helper functions ---


async def _get_block_from_db(ip: str) -> BlockedEntity | None:
	blocks = get_collection(MongoDBCollection.BLOCKED_ENTITIES)
	block_doc = await blocks.find_one(
		{
			'entity_type': BlockedEntityType.IP,
			'entity_id': ip,
		},
		{'_id': 0},
	)
	if block_doc:
		return BlockedEntity.model_validate(block_doc)
	return None


async def _get_stats_from_db(ip: str) -> IpUsageStats | None:
	ip_stats = get_collection(MongoDBCollection.IP_USAGE_STATS)
	stats_doc = await ip_stats.find_one(
		{
			'ip_address': ip,
		},
		{'_id': 0},
	)
	if stats_doc:
		return IpUsageStats.model_validate(stats_doc)
	return None


# --- Test cases ---


async def test_update_latest_request_increments(
	ip_observer: IpObserver,
):
	ip = gen_test_ip()

	block = await ip_observer.update_latest_request(ip)
	assert block is None

	stats = ip_observer._ip_usage_stats.get(ip)
	assert stats is not None
	assert stats.requests_today == 1
	assert stats.last_api_request_at is not None


async def test_per_minute_rl_blocks(
	ip_observer: IpObserver,
):
	ip = gen_test_ip()

	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_IP + 1):
		block = await ip_observer.update_latest_request(ip)

	assert block is not None
	assert block.entity_id == ip
	assert block.entity_type == 'ip'
	assert block.reason


async def test_block_persists_to_db(
	ip_observer: IpObserver,
):
	ip = gen_test_ip()

	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_IP + 1):
		block = await ip_observer.update_latest_request(ip)

	assert block is not None

	# Wait for async write-back.
	await ip_observer._db_write_back_queue.join()

	block = await _get_block_from_db(ip)
	assert block is not None
	assert block.entity_id == ip


async def test_expired_block_is_removed(
	ip_observer: IpObserver,
):
	ip = gen_test_ip()

	# Force a block.
	block = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_IP + 1):
		block = await ip_observer.update_latest_request(ip)

	assert block is not None

	# Expire it in memory.
	mem_block = ip_observer._blocked_ips[ip]
	mem_block.blocked_until = 0

	res = await ip_observer.is_ip_blocked(ip)
	assert res is None

	await ip_observer._db_write_back_queue.join()

	block = await _get_block_from_db(ip)
	assert block is None


async def test_cleanup_removes_old_stats(
	ip_observer: IpObserver,
):
	ip = gen_test_ip()

	# Update latest request to create stats.
	await ip_observer.update_latest_request(ip)

	# Manualy set last request time to be old.
	stats = ip_observer._ip_usage_stats.get(ip)
	assert stats is not None
	stats.last_api_request_at = 0

	# Manually run cleanup.
	await ip_observer._cleanup()

	# Check if stats were removed from memory.
	assert ip not in ip_observer._ip_usage_stats
	# Check if stats were removed from the database.
	db_stats = await _get_stats_from_db(ip)
	assert db_stats is None
