"""
This module acts as the main entry point for the
Mwalika Agent API server, initializing the FastAPI
application and running the server with the appropriate
configuration based on the environment.
"""

from os import getenv

from api.lifecycle.environment import load_environment
from shared.logging import LogStyle, cprint

# --- Load environment and perform checks ---

load_environment()

# --- Run server ---

if __name__ == '__main__':
	import uvicorn

	env = getenv('MWALIKA_ENV', '')
	port = int(getenv('MWALIKA_SERVER_PORT', ''))
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
			workers=1,
			reload=True,
		)
	elif env == 'testing':
		uvicorn.run(
			app='api.server:app',
			host='0.0.0.0',
			port=port,
			log_level='debug',
			workers=1,
			reload=False,
		)
