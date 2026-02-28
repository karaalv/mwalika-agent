"""
This module contains test fixtures for the WebSocket
API routes in the Mwalika Agent system, including
fixtures for starting a test server instance in
a separate process which the WebSocket client can connect to.
"""

import os
import signal
import socket
import subprocess
import time
from collections.abc import Generator

import pytest

from shared.logging import LogStyle, cprint


def _free_port() -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind(('127.0.0.1', 0))
		return int(s.getsockname()[1])


def _wait_for_server(
	*,
	base_url: str,
	timeout_s: float = 10.0,
) -> None:
	import requests

	deadline = time.time() + timeout_s
	while time.time() < deadline:
		try:
			r = requests.get(f'{base_url}/system/health', timeout=0.5)
			if r.status_code == 200:
				return
			print('.', end='', flush=True)
		except Exception:
			time.sleep(0.1)

	raise RuntimeError(f'Server did not start within {timeout_s}s')


# --- Server instance fixture ---


@pytest.fixture(scope='package')
def server_instance() -> Generator[str, None, None]:
	"""
	Starts a real uvicorn server in another process and yields the
	base address, e.g. 127.0.0.1:51234

	Package-scoped so WS tests in a package share one server.
	"""
	port = _free_port()
	host = '127.0.0.1'
	base_addr = f'{host}:{port}'
	base_url = f'http://{base_addr}'

	env = os.environ.copy()
	env['MWALIKA_ENV'] = 'testing'
	env['MWALIKA_SERVER_PORT'] = str(port)

	cprint(
		message=(
			f'Starting test server instance '
			f'at {base_url} for WebSocket tests...'
		),
		style=LogStyle.INFO,
	)

	# Run server from entry point
	proc = subprocess.Popen(
		['python', 'run.py'],
		env=env,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)

	try:
		_wait_for_server(base_url=base_url)
		cprint(f'Test server is up at {base_url}', LogStyle.SUCCESS)
		yield base_addr
	finally:
		proc.send_signal(signal.SIGINT)
		try:
			proc.wait(timeout=5)
		except Exception:
			cprint(
				'Server did not shut down gracefully, killing...',
				LogStyle.WARNING,
			)
			proc.send_signal(signal.SIGKILL)
