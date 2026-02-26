"""
This module defines utility functions for extracting
and handling IP addresses from FastAPI requests and WebSocket
connections.
"""

from fastapi import Request, WebSocket


def get_http_ip(request: Request) -> str:
	"""
	Extract the client's IP address from a FastAPI HTTP request.
	Checks the 'X-Forwarded-For' header first (in case of proxies),
	then falls back to the client host information.
	"""
	x_forwarded_for = request.headers.get('X-Forwarded-For')
	if x_forwarded_for:
		# In case of multiple IPs, take the first one
		ip = x_forwarded_for.split(',')[0].strip()
	else:
		ip = request.client.host if request.client else 'unknown'
	return ip


def get_ws_ip(websocket: WebSocket) -> str:
	"""
	Extract the client's IP address from a FastAPI WebSocket
	connection. Checks the 'X-Forwarded-For' header first
	(in case of proxies), then falls back to the client host
	information.
	"""
	x_forwarded_for = websocket.headers.get('X-Forwarded-For')
	if x_forwarded_for:
		# In case of multiple IPs, take the first one
		ip = x_forwarded_for.split(',')[0].strip()
	else:
		ip = websocket.client.host if websocket.client else 'unknown'
	return ip
