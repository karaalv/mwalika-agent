"""
This module contains schemas for the FAQ data
scraped from the eCitizen website.
"""

from pydantic import BaseModel, ConfigDict, Field


class FAQEntry(BaseModel):
	"""
	Schema for FAQ entries in the FAQ entity.
	"""

	model_config = ConfigDict(
		extra='forbid',
		str_strip_whitespace=True,
	)

	faq_id: str = Field(
		...,
		description=(
			'Identifier derived from hash of '
			'`question-answer`.'
		),
	)
	qdrant_id: str | None = Field(
		default=None,
		description=(
			'Unique identifier for the corresponding point '
			'in QdrantDB.'
		),
	)
	question: str = Field(
		...,
		description=(
			'FAQ question text as listed on '
			'the eCitizen platform.'
		),
	)
	answer: str = Field(
		...,
		description=('Corresponding FAQ answer text.'),
	)
