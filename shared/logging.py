"""
Shared console utilities using Rich.

This module is separate from structured logging
and Sentry-based error tracking.
"""

import traceback
from enum import Enum

from rich.console import Console
from rich.theme import Theme

# --- Log Styles ---


class LogStyle(str, Enum):
	DEFAULT = 'default'
	ERROR = 'error'
	SUCCESS = 'success'
	WARNING = 'warning'
	INFO = 'info'


# --- Theme Configuration ---


_theme = Theme(
	{
		'default': 'white',
		'error': 'bold red',
		'success': 'bold green',
		'warning': 'bold yellow',
		'info': 'bold blue',
	}
)


_console = Console(theme=_theme)


# --- Console Wrapper ---


def cprint(
	message: str,
	style: LogStyle = LogStyle.DEFAULT,
	prefix: str | None = None,
) -> None:
	if prefix:
		message = f'[{prefix}] {message}'
	_console.print(message, style=style.value)


# --- Exception formatting ---


def format_exception(e: BaseException) -> str:
	"""
	Formats exception details into a string
	for logging error information in detail.

	Args:
	e (BaseException): The exception to format.

	Returns:
	str: A formatted string containing exception
		details.
	"""
	lines: list[str] = []
	lines.append(f'type={type(e)!r}')
	lines.append(f'repr={e!r}')

	cause = getattr(e, '__cause__', None)
	ctx = getattr(e, '__context__', None)

	if cause is not None:
		lines.append(f'cause_type={type(cause)!r}')
		lines.append(f'cause_repr={cause!r}')

	if ctx is not None:
		lines.append(f'context_type={type(ctx)!r}')
		lines.append(f'context_repr={ctx!r}')

	lines.append('traceback:')
	lines.append(traceback.format_exc())
	return '\n'.join(lines)
