"""
Shared console utilities using Rich.

This module is separate from structured logging
and Sentry-based error tracking.
"""

from enum import Enum

from rich.console import Console
from rich.theme import Theme

# --- Log Styles ---


class LogStyle(Enum):
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
