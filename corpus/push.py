"""
This module contains the main logic for
pushing data into QdrantDB and MongoDB,
including point creation and upsert operations.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from corpus.worker import CorpusWorker
from databases.mongodb.config import (
	close_mongodb_client,
	start_mongodb_client,
)
from databases.qdrant.config import (
	close_qdrant_client,
	start_qdrant_client,
)
from openai_client.config import (
	close_openai_client,
	start_openai_client,
)
from shared.logging import (
	LogStyle,
	cprint,
	format_exception,
)

load_dotenv(override=True, dotenv_path=os.path.abspath('.env.dev'))

# --- Helpers ---


def _find_repo_root(start: Path) -> Path:
	for p in (start, *start.parents):
		if (p / 'pyproject.toml').is_file():
			return p
		if (p / '.git').exists():
			return p
	raise RuntimeError('Repo root not found')


def _resolve_data_path() -> Path:
	env = os.getenv('MWALIKA_DATA_PATH')
	if env:
		return Path(env).expanduser().resolve()

	here = Path(__file__).resolve()
	root = _find_repo_root(here)
	return (root / 'data').resolve()


# --- Main execution ---


async def main() -> None:
	"""Main function to run the corpus worker."""
	cprint(
		'Starting corpus worker...',
		style=LogStyle.INFO,
		prefix='corpus.worker',
	)

	# Start clients
	start_openai_client()
	start_qdrant_client()
	await start_mongodb_client()

	# Data path
	data_path = _resolve_data_path()
	try:
		worker = CorpusWorker(data_path=data_path)
		await worker.run()
	except Exception as e:
		cprint(
			'An error occurred during corpus processing.',
			style=LogStyle.ERROR,
			prefix='corpus.worker',
		)
		cprint(
			format_exception(e),
			style=LogStyle.ERROR,
			prefix='corpus.worker',
		)
	finally:
		# Close clients
		await close_mongodb_client()
		await close_qdrant_client()
		await close_openai_client()


if __name__ == '__main__':
	asyncio.run(main())
