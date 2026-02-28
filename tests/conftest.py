"""
This module contains configuration and
fixtures for testing the Mwalika Agent.
"""

import os

import pytest_asyncio
from dotenv import load_dotenv

from tests.config.conftest_utils import (
	close_test_clients,
	init_test_clients,
)

load_dotenv(override=True, dotenv_path=os.path.abspath('.env.test'))

# --- Async client fixtures ---


@pytest_asyncio.fixture(scope='session', autouse=True)
async def setup_async_clients():
	"""
	Fixture to initialize async clients for
	MongoDB, QdrantDB, and OpenAI.
	"""

	await init_test_clients()

	yield

	await close_test_clients()
