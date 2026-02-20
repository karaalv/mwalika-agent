"""
This module is used for testing the agent
using manual terminal input and output, without
relying on a full websocket client setup.
"""

import asyncio
import os
import signal
import sys

from dotenv import load_dotenv

from agent.main import agent_chat
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
from shared.logging import LogStyle, cprint
from tests.utils.mongodb import clear_test_databases

load_dotenv(override=True, dotenv_path=os.path.abspath('.env.test'))

# --- Lifecycle management ---


async def _setup() -> None:
	cprint(
		'Setting up test environment...',
		style=LogStyle.INFO,
	)
	await start_mongodb_client()
	start_qdrant_client()
	start_openai_client()
	await clear_test_databases()
	cprint(
		'Test environment setup complete.',
		style=LogStyle.SUCCESS,
	)


async def _teardown() -> None:
	cprint(
		'Tearing down test environment...',
		style=LogStyle.INFO,
	)
	await clear_test_databases()
	await close_mongodb_client()
	await close_qdrant_client()
	await close_openai_client()
	cprint(
		'Test environment teardown complete.',
		style=LogStyle.SUCCESS,
	)


def _signal_handler() -> None:
	def signal_handler(signum, frame):
		cprint(
			f'Received signal {signum}, shutting down...',
			style=LogStyle.WARNING,
		)
		# Perform cleanup

		# Create new event loop for cleanup since we might
		# be in a different thread
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		loop.run_until_complete(_teardown())
		loop.close()
		sys.exit(0)

	signal.signal(signal.SIGTERM, signal_handler)
	# Handle Ctrl+C as well
	signal.signal(signal.SIGINT, signal_handler)


# --- Main execution ---


async def main():
	_signal_handler()
	await _setup()
	cprint(
		'Entering main loop. Press Ctrl+C to exit.',
		style=LogStyle.DEFAULT,
	)

	try:
		while True:
			user_input = input('> ')
			if user_input.lower() in ['exit', 'quit']:
				cprint('Exiting...', style=LogStyle.INFO)
				break
			await agent_chat(
				user_id='test_user',
				session_id='test_chat',
				user_input=user_input,
				verbosity_level=1,
			)
	except Exception as e:
		cprint(f'Error: {e}', style=LogStyle.ERROR)
	finally:
		cprint('Cleaning up...', style=LogStyle.INFO)
		await _teardown()


if __name__ == '__main__':
	asyncio.run(main())
