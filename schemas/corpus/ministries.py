"""
This module contains schemas for the ministries data
scraped from the eCitizen website.
"""

from pydantic import BaseModel, ConfigDict, Field


class MinistryEntry(BaseModel):
	"""
	Schema for Ministry entries in the
	ministries entity.
	"""

	model_config = ConfigDict(
		extra='forbid',
		str_strip_whitespace=True,
	)

	ministry_id: str = Field(
		...,
		description=(
			'Identifier derived from normalised '
			'ministry name.'
		),
	)
	qdrant_id: str | None = Field(
		default=None,
		description=(
			'Unique identifier for the corresponding point '
			'in QdrantDB.'
		),
	)
	ministry_name: str = Field(
		...,
		description=(
			'Ministry name as listed on the eCitizen '
			'platform.'
		),
	)
	ministry_description: str | None = Field(
		...,
		description=('Public ministry description.'),
	)
	ministry_description_summary: str | None = Field(
		default=None,
		description=(
			'Concise summary of the ministry description, '
			'limited to 150 tokens.'
		),
	)
	reported_agency_count: int | None = Field(
		...,
		description=(
			'Agency count reported by the eCitizen '
			'platform.'
		),
	)
	observed_agency_count: int | None = Field(
		...,
		description=(
			'Agency count observed in the dataset.'
		),
	)
	reported_service_count: int | None = Field(
		...,
		description=(
			'Service count reported by the eCitizen '
			'platform.'
		),
	)
	observed_service_count: int | None = Field(
		...,
		description=(
			'Service count observed in the dataset.'
		),
	)
	observed_department_count: int | None = Field(
		...,
		description=(
			'Department count observed in the dataset.'
		),
	)

	ministry_url: str = Field(
		...,
		description=(
			'URL of ministry page on the eCitizen platform.'
		),
	)
