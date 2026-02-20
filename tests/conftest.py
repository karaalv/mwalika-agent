"""
This module contains configuration and
fixtures for testing the Mwalika Agent.
"""

import os
from asyncio import sleep

import pytest_asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pymongo import AsyncMongoClient
from qdrant_client import AsyncQdrantClient

from databases.mongodb.config import (
	close_mongodb_client,
	set_mongodb_client,
)
from databases.qdrant.config import (
	close_qdrant_client,
	set_qdrant_client,
)
from openai_client.config import (
	close_openai_client,
	set_openai_client,
)
from shared.logging import (
	LogStyle,
	cprint,
)

load_dotenv(override=True, dotenv_path=os.path.abspath('.env.test'))

# --- Async client fixtures ---


async def _init_mongo_test_client() -> None:
	mongo_uri = os.getenv('MONGODB_URI')
	if not mongo_uri:
		raise RuntimeError(
			'MONGODB_URI environment variable is not set.'
		)
	client = AsyncMongoClient(mongo_uri)
	await client.aconnect()
	set_mongodb_client(client)
	cprint(
		'MongoDB test client initialized.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


async def _init_qdrant_test_client() -> None:
	qdrant_url = os.getenv('QDRANT_URL')
	qdrant_api_key = os.getenv('QDRANT_API_KEY')
	if not qdrant_url:
		raise RuntimeError(
			'QDRANT_URL environment variable is not set.'
		)
	client = AsyncQdrantClient(
		url=qdrant_url,
		api_key=qdrant_api_key,
	)
	set_qdrant_client(client)
	cprint(
		'QdrantDB test client initialized.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


async def _init_openai_test_client() -> None:
	openai_api_key = os.getenv('OPENAI_API_KEY')
	if not openai_api_key:
		raise RuntimeError(
			'OPENAI_API_KEY environment variable is not set.'
		)
	client = AsyncOpenAI(api_key=openai_api_key)
	set_openai_client(client)
	cprint(
		'OpenAI test client initialized.',
		style=LogStyle.SUCCESS,
		prefix='tests.conftest',
	)


@pytest_asyncio.fixture(scope='session', autouse=True)
async def setup_async_clients():
	"""
	Fixture to initialize async clients for
	MongoDB, QdrantDB, and OpenAI.
	"""

	await _init_mongo_test_client()
	await _init_qdrant_test_client()
	await _init_openai_test_client()

	yield

	await close_openai_client()
	await close_qdrant_client()
	await close_mongodb_client()

	# Ensure closure
	await sleep(1)
