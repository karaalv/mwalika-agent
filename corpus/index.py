"""
This module creates the search index in QdrantDB
for the corpus data.
"""

import asyncio
import os

from dotenv import load_dotenv
from qdrant_client.models import PayloadSchemaType

from databases.qdrant.config import (
	close_qdrant_client,
	get_qdrant_client,
	start_qdrant_client,
)

load_dotenv(override=True, dotenv_path=os.path.abspath('.env.dev'))


async def main() -> None:
	"""Main function to run the corpus worker."""
	print('Starting corpus worker...')
	start_qdrant_client()
	try:
		client = get_qdrant_client()
		await client.create_payload_index(
			collection_name='mwalika_corpus',
			field_name='type',
			field_schema=PayloadSchemaType.KEYWORD,
		)
	finally:
		await close_qdrant_client()


if __name__ == '__main__':
	asyncio.run(main())
