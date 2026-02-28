"""
This module contains test fixtures for the HTTP API
routes in the Mwalika Agent system, including
fixtures for running an Async HTTP client that serves
as the basis for testing the API endpoints.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from api.server import app

# --- FastAPI test client fixture ---


@pytest_asyncio.fixture(scope='session')
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
