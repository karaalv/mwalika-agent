"""
This module contains exception guarding decorators
for the Mwalika Agent system. These decorators are
designed to wrap functions and methods, providing
a consistent way to handle exceptions, log errors,
and integrate with observability tools like Sentry.
"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import sentry_sdk

from exceptions.core import (
	ApplicationException,
	ErrorContext,
)
from observability.sentry.helpers import (
	BreadcrumbLevel,
	add_breadcrumb,
	set_tags,
)

# Decorator type definitions
P = ParamSpec('P')
R = TypeVar('R')

logger = logging.getLogger(__name__)


def guard(
	operation: str,
	component: str,
	code: str,
	meta: dict[str, Any] | None = None,
	wrap_cls: type[ApplicationException] = ApplicationException,
	map_exc: Callable[[BaseException], type[ApplicationException]]
	| None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
	def decorator(fn: Callable[P, R]) -> Callable[P, R]:
		@wraps(fn)
		def wrapped(*a: P.args, **kw: P.kwargs) -> R:
			tags = {
				'component': component,
				'operation': operation,
				'code': code,
			}

			try:
				return fn(*a, **kw)

			except ApplicationException as e:
				# All subclasses land here
				logger.exception(
					'App error %s:%s (%s) in %s',
					component,
					operation,
					code,
					fn.__name__,
				)
				# Add tags and breadcrumbs for sentry
				with sentry_sdk.push_scope():
					set_tags(tags, metadata=meta)
					add_breadcrumb(
						category=f'{component}:{operation}',
						message=f'Failure in {fn.__name__}',
						level=BreadcrumbLevel.ERROR,
					)
					sentry_sdk.capture_exception(e)
				raise

			except Exception as e:
				logger.exception(
					'Error %s:%s (%s) in %s',
					component,
					operation,
					code,
					fn.__name__,
				)
				# Add tags and breadcrumbs for sentry
				with sentry_sdk.push_scope():
					set_tags(tags, metadata=meta)
					add_breadcrumb(
						category=f'{component}:{operation}',
						message=f'Failure in {fn.__name__}',
						level=BreadcrumbLevel.ERROR,
					)
					sentry_sdk.capture_exception(e)

				cls = wrap_cls
				if map_exc is not None:
					cls = map_exc(e)

				raise cls(
					message=(f'Error in {component}:{operation}'),
					code=code,
					context=ErrorContext(
						operation=operation,
						component=component,
						metadata=meta,
					),
					cause=e,
				) from e

		return wrapped

	return decorator


def guard_async(
	operation: str,
	component: str,
	code: str,
	meta: dict[str, Any] | None = None,
	wrap_cls: type[ApplicationException] = ApplicationException,
	map_exc: Callable[[BaseException], type[ApplicationException]]
	| None = None,
) -> Callable[
	[Callable[P, Awaitable[R]]],
	Callable[P, Awaitable[R]],
]:
	def deco(
		fn: Callable[P, Awaitable[R]],
	) -> Callable[P, Awaitable[R]]:
		@wraps(fn)
		async def wrapped(*a: P.args, **kw: P.kwargs) -> R:
			tags = {
				'component': component,
				'operation': operation,
				'code': code,
			}

			try:
				return await fn(*a, **kw)

			except ApplicationException as e:
				logger.exception(
					'App error %s:%s (%s) in %s',
					component,
					operation,
					code,
					fn.__name__,
				)
				# Add tags and breadcrumbs for sentry
				with sentry_sdk.new_scope():
					set_tags(tags, metadata=meta)
					add_breadcrumb(
						category=f'{component}:{operation}',
						message=f'Failure in {fn.__name__}',
						level=BreadcrumbLevel.ERROR,
					)
					sentry_sdk.capture_exception(e)
				raise

			except Exception as e:
				logger.exception(
					'Error %s:%s (%s) in %s',
					component,
					operation,
					code,
					fn.__name__,
				)
				# Add tags and breadcrumbs for sentry
				with sentry_sdk.new_scope():
					set_tags(tags, metadata=meta)
					add_breadcrumb(
						category=f'{component}:{operation}',
						message=f'Failure in {fn.__name__}',
						level=BreadcrumbLevel.ERROR,
					)
					sentry_sdk.capture_exception(e)

				cls = wrap_cls
				if map_exc is not None:
					cls = map_exc(e)

				raise cls(
					message=(f'Error in {component}:{operation}'),
					code=code,
					context=ErrorContext(
						operation=operation,
						component=component,
						metadata=meta,
					),
					cause=e,
				) from e

		return wrapped

	return deco
