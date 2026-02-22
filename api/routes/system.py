"""
This module contains system-related API routes,
such as health checks and status endpoints.
"""

from fastapi import APIRouter
from fastapi.requests import Request

from api.utils.responses import http_response

# --- Router setup ---

system_router = APIRouter()

# --- API routes ---


@system_router.get('/health')
async def health_check(request: Request):
	"""
	Health check endpoint to verify that the API server is running.
	Returns a simple success message if the server is healthy.
	"""
	request_id = getattr(request.state, 'request_id', '')
	return http_response(
		request_id=request_id,
		success=True,
		message='Mwalika Agent API is healthy',
	)
