# ruff: noqa: E402
"""
This module contains the logic for pushing
data into MongoDB only for the corpus.

Run like:

	mwalika_env=production python -m corpus.push_mongodb_only

Supported environments:
- production
- testing
- development
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Helpers ---


def _find_repo_root(start: Path) -> Path:
	for p in (start, *start.parents):
		if (p / 'pyproject.toml').is_file():
			return p
		if (p / '.git').exists():
			return p
	raise RuntimeError('Repo root not found')


def _get_runtime_env() -> str:
	"""
	Read the environment selector from either:
	- mwalika_env
	- MWALIKA_ENV

	Lowercase is supported because the intended
	run command uses:
		mwalika_env=production python -m ...
	"""
	env = (
		os.getenv('mwalika_env')
		or os.getenv('MWALIKA_ENV')
		or 'development'
	)

	return env.strip().lower()


def _resolve_env_file(repo_root: Path, env: str) -> Path:
	"""
	Map the runtime environment to the correct
	dotenv file.

	Adjust these filenames if your repo uses a
	different naming convention.
	"""
	candidates: dict[str, list[str]] = {
		'production': [
			'.env.production',
			'.env.prod',
		],
		'testing': [
			'.env.test',
			'.env.testing',
		],
		'test': [
			'.env.test',
			'.env.testing',
		],
		'development': [
			'.env.development',
			'.env.dev',
			'.env.local',
			'.env',
		],
		'dev': [
			'.env.development',
			'.env.dev',
			'.env.local',
			'.env',
		],
		'local': [
			'.env.local',
			'.env.development',
			'.env',
		],
	}

	file_names = candidates.get(env)
	if file_names is None:
		raise RuntimeError(
			f"Unsupported mwalika_env '{env}'. "
			'Expected one of: production, testing, development.'
		)

	for file_name in file_names:
		path = repo_root / file_name
		if path.is_file():
			return path

	raise RuntimeError(
		f"No dotenv file found for mwalika_env='{env}'. "
		f'Tried: {file_names}'
	)


def _load_runtime_env() -> str:
	"""
	Load the correct dotenv file before any config
	modules are imported.
	"""
	here = Path(__file__).resolve()
	repo_root = _find_repo_root(here)

	runtime_env = _get_runtime_env()
	env_file = _resolve_env_file(repo_root, runtime_env)

	load_dotenv(dotenv_path=env_file, override=True)

	# Keep both names available after loading so the
	# rest of the app can consistently use MWALIKA_ENV.
	os.environ['MWALIKA_ENV'] = runtime_env
	os.environ['mwalika_env'] = runtime_env

	return runtime_env


def _resolve_data_path() -> Path:
	env = os.getenv('MWALIKA_DATA_PATH')
	if env:
		return Path(env).expanduser().resolve()

	here = Path(__file__).resolve()
	root = _find_repo_root(here)
	return (root / 'data').resolve()


# IMPORTANT:
# Load env before importing modules that may depend
# on environment variables during import time.
RUNTIME_ENV = _load_runtime_env()


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

# --- Main execution ---


async def main() -> None:
	"""Main function to run the corpus worker."""
	cprint(
		f"Starting corpus worker in '{RUNTIME_ENV}' mode...",
		style=LogStyle.INFO,
		prefix='corpus.worker',
	)

	start_openai_client()
	start_qdrant_client()
	await start_mongodb_client()

	data_path = _resolve_data_path()

	try:
		worker = CorpusWorker(data_path=data_path)
		await worker._push_to_mongodb()
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
		await close_mongodb_client()
		await close_qdrant_client()
		await close_openai_client()


if __name__ == '__main__':
	asyncio.run(main())
