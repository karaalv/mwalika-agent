"""
This module contains configuration and
fixtures for testing the Mwalika Agent.
"""

import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from api.server import app
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

	# Ensure closure
	# await sleep(1)


# --- FastAPI test client fixture ---


@pytest.fixture(scope='session')
async def http_client() -> AsyncGenerator[AsyncClient, None]:
	"""
	Fixture to provide an HTTP client for testing
	the FastAPI application.
	"""
	async with LifespanManager(app):
		transport = ASGITransport(app=app)
		async with AsyncClient(
			transport=transport, base_url='http://test'
		) as client:
			yield client


@pytest.fixture(scope='session')
def ws_client() -> Generator[TestClient, None, None]:
	"""
	Fixture to provide a WebSocket client for testing
	the FastAPI application.
	"""
	with TestClient(app) as client:
		yield client
