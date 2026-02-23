"""
This module is the main entry point
for the Mwalika Agent API server.
"""

import os
from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api.dependencies.ratelimit import rate_limit_ip
from api.lifecycle.config import (
	check_environment,
	shutdown,
	startup,
)
from api.middleware.request_id import RequestIdMiddleware
from api.routes.agent import agent_router
from api.routes.system import system_router
from api.routes.users import users_router
from api.utils.responses import http_response
from exceptions.api import APIException
from exceptions.core import ErrorContext
from schemas.security.ratelimit import ResourcePolicyType
from shared.logging import LogStyle, cprint

# Load environment
if os.getenv('MWALIKA_ENV') == 'testing':
	load_dotenv(
		override=True,
		dotenv_path=os.path.abspath('.env.test'),
	)
elif os.getenv('MWALIKA_ENV') == 'production':
	load_dotenv(
		override=True,
		dotenv_path=os.path.abspath('.env.prod'),
	)
elif os.getenv('MWALIKA_ENV') == 'development':
	load_dotenv(
		override=True,
		dotenv_path=os.path.abspath('.env.dev'),
	)
else:
	raise APIException(
		message=(
			'Invalid MWALIKA_ENV value. '
			'Must be "production", "testing", '
			'or "development".'
		),
		code='invalid_environment',
		context=ErrorContext(
			operation='load_environment',
			component='api.server',
			metadata={'MWALIKA_ENV': os.getenv('MWALIKA_ENV')},
		),
	)

# Check environment validity
check_environment()

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

# --- Run server ---

if __name__ == '__main__':
	import uvicorn

	env = os.getenv('MWALIKA_ENV', '')
	port = int(os.getenv('MWALIKA_SERVER_PORT', ''))
	cprint(
		message=(
			f'Starting API server on port '
			f'{port} in {env} environment...'
		),
		style=LogStyle.INFO,
		prefix='api.server',
	)

	if env == 'production':
		uvicorn.run(
			app='api.server:app',
			host='0.0.0.0',
			port=port,
			log_level='info',
			workers=1,
			reload=False,
		)
	elif env == 'development':
		uvicorn.run(
			app='api.server:app',
			host='0.0.0.0',
			port=port,
			log_level='debug',
			reload=True,
		)
	elif env == 'testing':
		uvicorn.run(
			app='api.server:app',
			host='0.0.0.0',
			port=port,
			log_level='debug',
			reload=False,
		)
