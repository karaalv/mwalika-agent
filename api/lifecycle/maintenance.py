"""
This module contains the lifecycle management for the
servers maintenance resources (e.g., background tasks
for cleanup, retention, etc).
"""

from api.maintenance.limiter_store_pruner import LimiterStorePruner
from api.maintenance.user_data_pruner import UserDataPruner
from exceptions.api import ApiMaintenanceException
from exceptions.core import ErrorContext
from shared.logging import LogStyle, cprint

# --- Global instances ---

limiter_store_pruner: LimiterStorePruner | None = None
user_data_pruner: UserDataPruner | None = None


# --- Lifecycle management ---


def start_maintenance_tasks() -> None:
	_start_limiter_store_pruner()
	_start_user_data_pruner()


def _start_limiter_store_pruner() -> None:
	global limiter_store_pruner
	if limiter_store_pruner is None:
		limiter_store_pruner = LimiterStorePruner()
		try:
			limiter_store_pruner.start()
			cprint(
				'Limiter store pruner started.',
				style=LogStyle.SUCCESS,
				prefix='api.lifecycle',
			)
		except Exception as e:
			raise ApiMaintenanceException(
				code='limiter_store_pruner_start_failed',
				message='Failed to start limiter store pruner.',
				context=ErrorContext(
					operation='start_limiter_store_pruner',
					component='api.lifecycle',
				),
				cause=e,
			) from e


def _start_user_data_pruner() -> None:
	global user_data_pruner
	if user_data_pruner is None:
		user_data_pruner = UserDataPruner()
		try:
			user_data_pruner.start()
			cprint(
				'User data pruner started.',
				style=LogStyle.SUCCESS,
				prefix='api.lifecycle',
			)
		except Exception as e:
			raise ApiMaintenanceException(
				code='user_data_pruner_start_failed',
				message='Failed to start user data pruner.',
				context=ErrorContext(
					operation='start_user_data_pruner',
					component='api.lifecycle',
				),
				cause=e,
			) from e


async def stop_maintenance_tasks() -> None:
	await _stop_limiter_store_pruner()
	await _stop_user_data_pruner()


async def _stop_limiter_store_pruner() -> None:
	global limiter_store_pruner
	if limiter_store_pruner is not None:
		try:
			await limiter_store_pruner.stop()
			cprint(
				'Limiter store pruner stopped.',
				style=LogStyle.SUCCESS,
				prefix='api.lifecycle',
			)
		except Exception as e:
			raise ApiMaintenanceException(
				code='limiter_store_pruner_stop_failed',
				message='Failed to stop limiter store pruner.',
				context=ErrorContext(
					operation='stop_limiter_store_pruner',
					component='api.lifecycle',
				),
				cause=e,
			) from e
		finally:
			limiter_store_pruner = None


async def _stop_user_data_pruner() -> None:
	global user_data_pruner
	if user_data_pruner is not None:
		try:
			await user_data_pruner.stop()
			cprint(
				'User data pruner stopped.',
				style=LogStyle.SUCCESS,
				prefix='api.lifecycle',
			)
		except Exception as e:
			raise ApiMaintenanceException(
				code='user_data_pruner_stop_failed',
				message='Failed to stop user data pruner.',
				context=ErrorContext(
					operation='stop_user_data_pruner',
					component='api.lifecycle',
				),
				cause=e,
			) from e
		finally:
			user_data_pruner = None
