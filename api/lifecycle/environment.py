"""
This module is used to load the server environment
variables and perform any necessary checks to ensure
the environment is properly configured for the API server
to run.
"""

import os

from dotenv import load_dotenv

# --- Constants ---

_ENV_TO_FILE = {
	'testing': '.env.test',
	'production': '.env.prod',
	'development': '.env.dev',
}

_is_loaded = False

# --- Environment loading ---


def load_environment() -> str:
	# If environment is already loaded,
	# return the current environment
	global _is_loaded
	if _is_loaded:
		return os.getenv('MWALIKA_ENV', '')

	env = os.getenv('MWALIKA_ENV', '')

	if env not in _ENV_TO_FILE:
		raise RuntimeError(
			f'Invalid MWALIKA_ENV: {env}. '
			f'Must be one of: {", ".join(_ENV_TO_FILE.keys())}'
		)

	path = _ENV_TO_FILE.get(env)
	if path is None:
		raise RuntimeError(f'Invalid MWALIKA_ENV: {env}')

	load_dotenv(
		dotenv_path=os.path.abspath(path),
		override=True,
	)

	# Check environment validity
	check_environment()
	_is_loaded = True

	return env


# --- Environment checks ---


def check_environment() -> None:
	env = os.getenv('MWALIKA_ENV', '')
	if env not in _ENV_TO_FILE:
		raise RuntimeError(
			f'Invalid MWALIKA_ENV: {env}. '
			f'Must be one of: {", ".join(_ENV_TO_FILE.keys())}'
		)

	port = os.getenv('MWALIKA_SERVER_PORT')
	if port is None or not port.isdigit():
		raise RuntimeError(
			f'Invalid MWALIKA_SERVER_PORT: {port}. '
			f'Must be a valid integer port number.'
		)

	jwt_secret = os.getenv('JWT_SECRET')
	if not jwt_secret:
		raise RuntimeError(
			'JWT_SECRET environment variable must be set.'
		)
