"""
This module is the main entry point
for the Mwalika Agent API server.
"""

import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api.dependencies.ratelimit import rate_limit_ip
from api.lifecycle.config import (
	shutdown,
	startup,
)
from api.middleware.request_id import RequestIdMiddleware
from api.routes.agent import agent_router
from api.routes.system import system_router
from api.routes.users import users_router
from api.utils.responses import http_response
from exceptions.api import APIException
from schemas.security.ratelimit import ResourcePolicyType
from shared.logging import LogStyle, cprint

# --- Lifecycle management ---


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""
	Defines the lifespan of the API server,
	including startup and shutdown.
	"""
	env = os.getenv('MWALIKA_ENV', 'unknown')
	cprint(
		message=(
			f'Starting API server lifecycle in {env} environment...'
		),
		style=LogStyle.INFO,
		prefix='api.lifecycle',
	)
	await startup()

	yield

	cprint(
		'Shutting down API server lifecycle...',
		style=LogStyle.INFO,
		prefix='api.lifecycle',
	)
	await shutdown()


# --- App initialization ---

app = FastAPI(
	title='Mwalika Agent API',
	description=(
		'API server for the Mwalika Agent, handling '
		'incoming requests, managing WebSocket '
		'connections, and orchestrating interactions '
		'between components.'
	),
	version='1.0.0',
	lifespan=lifespan,
	root_path='/api',
)


# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(
	request: Request, exc: APIException
) -> JSONResponse:
	sentry_sdk.capture_exception(exc)
	return http_response(
		request_id=getattr(request.state, 'request_id', ''),
		success=False,
		message=exc.message,
		data={
			'code': exc.code,
			'context': exc.context.model_dump(mode='json'),
		},
		status_code=400,
	)


@app.exception_handler(HTTPException)
async def http_exception_handler(
	request: Request, exc: HTTPException
) -> JSONResponse:
	sentry_sdk.capture_exception(exc)
	return http_response(
		request_id=getattr(request.state, 'request_id', ''),
		success=False,
		message=exc.detail,
		data={},
		status_code=exc.status_code,
	)


@app.exception_handler(Exception)
async def general_exception_handler(
	request: Request, exc: Exception
) -> JSONResponse:
	sentry_sdk.capture_exception(exc)
	return http_response(
		request_id=getattr(request.state, 'request_id', ''),
		success=False,
		message=str(exc),
		data={},
		status_code=500,
	)


# --- Middleware ---

# Cors configuration
origins_raw = os.getenv('CORS_ORIGINS', '').split(',')
origins = [origin.strip() for origin in origins_raw if origin.strip()]
app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
)

# Request ID middleware
app.add_middleware(RequestIdMiddleware)


# --- Route imports ---

app.include_router(
	router=system_router,
	prefix='/system',
	tags=['System'],
	dependencies=[Depends(rate_limit_ip(ResourcePolicyType.SYSTEM))],
)

app.include_router(
	router=agent_router,
	prefix='/agent',
	tags=['Agent'],
)

app.include_router(
	router=users_router, prefix='/users', tags=['Users']
)
