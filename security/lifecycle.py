"""
This module defines lifecycle management utilities for the security
system, including startup and shutdown of components, as well as
environment checks. This file acts as the singleton entry point for
interacting with the security system's lifecycle.
"""

from exceptions.core import ErrorContext
from exceptions.security import SecurityServiceException
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb_capture_exception,
)
from schemas.security.observers import BlockedEntity
from schemas.security.tokens import TokenType
from security.observers.ip_observer import IpObserver
from security.observers.token_observer import TokenObserver
from security.observers.user_observer import UserObserver
from shared.logging import LogStyle, cprint

# --- Global instances ---

_ip_observer: IpObserver | None = None
_token_observer: TokenObserver | None = None
_user_observer: UserObserver | None = None

# --- Lifecycle management ---

# Connection management functions


async def start_security_system() -> None:
	"""Initializes all security-related components."""
	await _start_ip_observer()
	await _start_token_observer()
	await _start_user_observer()


async def _start_ip_observer() -> None:
	"""Starts the global IP observer instance."""
	global _ip_observer
	if _ip_observer is None:
		_ip_observer = IpObserver()
		try:
			await _ip_observer.start()
			cprint(
				'IP observer started.',
				style=LogStyle.SUCCESS,
				prefix='security.lifecycle',
			)
		except Exception as e:
			raise SecurityServiceException(
				code='ip_observer_start_failed',
				message='Failed to start IP observer.',
				context=ErrorContext(
					operation='start_ip_observer',
					component='security.lifecycle',
				),
				cause=e,
			) from e


async def _start_token_observer() -> None:
	"""Starts the global token observer instance."""
	global _token_observer
	if _token_observer is None:
		_token_observer = TokenObserver()
		try:
			await _token_observer.start()
			cprint(
				'Token observer started.',
				style=LogStyle.SUCCESS,
				prefix='security.lifecycle',
			)
		except Exception as e:
			raise SecurityServiceException(
				code='token_observer_start_failed',
				message='Failed to start token observer.',
				context=ErrorContext(
					operation='start_token_observer',
					component='security.lifecycle',
				),
				cause=e,
			) from e


async def _start_user_observer() -> None:
	"""Starts the global user observer instance."""
	global _user_observer
	if _user_observer is None:
		_user_observer = UserObserver()
		try:
			await _user_observer.start()
			cprint(
				'User observer started.',
				style=LogStyle.SUCCESS,
				prefix='security.lifecycle',
			)
		except Exception as e:
			raise SecurityServiceException(
				code='user_observer_start_failed',
				message='Failed to start user observer.',
				context=ErrorContext(
					operation='start_user_observer',
					component='security.lifecycle',
				),
				cause=e,
			) from e


async def stop_security_system() -> None:
	"""Shuts down all security-related components gracefully."""
	await _close_ip_observer()
	await _close_token_observer()
	await _close_user_observer()


async def _close_ip_observer() -> None:
	"""Closes the global IP observer instance."""
	global _ip_observer
	if _ip_observer is not None:
		try:
			await _ip_observer.stop()
			cprint(
				'IP observer stopped.',
				style=LogStyle.SUCCESS,
				prefix='security.lifecycle',
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='security.lifecycle',
				cause=e,
				message='Failed to stop IP observer.',
				level=BreadcrumbLevel.ERROR,
			)
		finally:
			_ip_observer = None


async def _close_token_observer() -> None:
	"""Closes the global token observer instance."""
	global _token_observer
	if _token_observer is not None:
		try:
			await _token_observer.stop()
			cprint(
				'Token observer stopped.',
				style=LogStyle.SUCCESS,
				prefix='security.lifecycle',
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='security.lifecycle',
				cause=e,
				message='Failed to stop token observer.',
				level=BreadcrumbLevel.ERROR,
			)
		finally:
			_token_observer = None


async def _close_user_observer() -> None:
	"""Closes the global user observer instance."""
	global _user_observer
	if _user_observer is not None:
		try:
			await _user_observer.stop()
			cprint(
				'User observer stopped.',
				style=LogStyle.SUCCESS,
				prefix='security.lifecycle',
			)
		except Exception as e:
			add_breadcrumb_capture_exception(
				category='security.lifecycle',
				cause=e,
				message='Failed to stop user observer.',
				level=BreadcrumbLevel.ERROR,
			)
		finally:
			_user_observer = None


# Setter functions for testing


def set_ip_observer(observer: IpObserver | None) -> None:
	"""Sets the global IP observer instance (for testing)."""
	global _ip_observer
	_ip_observer = observer


def set_token_observer(observer: TokenObserver | None) -> None:
	"""Sets the global token observer instance (for testing)."""
	global _token_observer
	_token_observer = observer


def set_user_observer(observer: UserObserver | None) -> None:
	"""Sets the global user observer instance (for testing)."""
	global _user_observer
	_user_observer = observer


# --- Accessor functions ---


def get_ip_observer() -> IpObserver:
	"""Returns the global IP observer instance."""
	if _ip_observer is None:
		raise SecurityServiceException(
			code='ip_observer_not_initialized',
			message='IP observer not initialized.',
			context=ErrorContext(
				operation='get_ip_observer',
				component='security.lifecycle',
			),
		)
	return _ip_observer


def get_token_observer() -> TokenObserver:
	"""Returns the global token observer instance."""
	if _token_observer is None:
		raise SecurityServiceException(
			code='token_observer_not_initialized',
			message='Token observer not initialized.',
			context=ErrorContext(
				operation='get_token_observer',
				component='security.lifecycle',
			),
		)
	return _token_observer


def get_user_observer() -> UserObserver:
	"""Returns the global user observer instance."""
	if _user_observer is None:
		raise SecurityServiceException(
			code='user_observer_not_initialized',
			message='User observer not initialized.',
			context=ErrorContext(
				operation='get_user_observer',
				component='security.lifecycle',
			),
		)
	return _user_observer


# --- Blocked inspections ---


async def is_ip_blocked(ip_address: str) -> BlockedEntity | None:
	"""Checks if the given IP address is currently blocked."""
	ip_observer = get_ip_observer()
	return await ip_observer.is_ip_blocked(ip_address)


async def is_rt_blocked(token_id: str) -> BlockedEntity | None:
	"""Checks if the given token is currently blocked."""
	token_observer = get_token_observer()
	return await token_observer.is_token_blocked(
		token_id, TokenType.REFRESH
	)


async def is_at_blocked(token_id: str) -> BlockedEntity | None:
	"""Checks if the given token is currently blocked."""
	token_observer = get_token_observer()
	return await token_observer.is_token_blocked(
		token_id, TokenType.ACCESS
	)


async def is_user_blocked(user_id: str) -> BlockedEntity | None:
	"""Checks if the given user ID is currently blocked."""
	user_observer = get_user_observer()
	return await user_observer.is_user_blocked(user_id)


# --- Update latest request


async def update_latest_ip_request(ip_address: str) -> None:
	"""
	Updates the latest request timestamp for the
	given IP address.
	"""
	ip_observer = get_ip_observer()
	await ip_observer.update_latest_request(ip_address)


async def update_latest_user_request(user_id: str) -> None:
	"""Updates the latest request timestamp for the given user ID."""
	user_observer = get_user_observer()
	await user_observer.update_latest_request(user_id)


async def update_latest_rt_request(token_id: str) -> None:
	"""
	Updates the latest request timestamp for the
	given refresh token.
	"""
	token_observer = get_token_observer()
	await token_observer.update_latest_rt_usage(token_id)


async def update_latest_at_request(token_id: str) -> None:
	"""
	Updates the latest request timestamp for the
	given access token.
	"""
	token_observer = get_token_observer()
	await token_observer.update_latest_at_usage(token_id)
