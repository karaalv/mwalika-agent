"""
This module defines core custom exceptions
for the Mwalika Agent system used across
various components to package and handle errors
in a consistent manner.
"""

from typing import Any

from pydantic import BaseModel


class ErrorContext(BaseModel):
	"""
	Contextual information about an
	error used for more informative
	error messages.
	"""

	# The operation being performed when the
	# error occurred
	operation: str
	# The component in which the error occurred
	component: str
	# Additional metadata about the error
	metadata: dict[str, Any] | None = None


class ApplicationException(Exception):
	def __init__(
		self,
		message: str,
		code: str,
		context: ErrorContext,
		cause: BaseException | None = None,
	) -> None:
		super().__init__(message)
		self.message = message
		self.code = code
		self.context = context
		self.cause = cause
		if cause is not None:
			self.__cause__ = cause

	def __str__(self) -> str:
		return (
			f'{self.code}: {self.message} '
			f'({self.context.component}:{self.context.operation})'
		)
