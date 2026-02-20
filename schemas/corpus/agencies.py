"""
This module contains schemas for the agencies
data scraped from the eCitizen website.
"""

from pydantic import BaseModel, ConfigDict, Field


class AgencyEntry(BaseModel):
	"""
	Schema for Agency entries in the agencies
	entity.
	"""

	model_config = ConfigDict(
		extra='forbid',
		str_strip_whitespace=True,
	)

	agency_id: str = Field(
		...,
		description=(
			'Identifier derived from '
			'`ministry_id-department_id-'
			'agency_name`.'
		),
	)
	agency_name_hash: str = Field(
		...,
		description=(
			'Identifier derived from normalised agency name only.'
		),
	)

	ministry_id: str = Field(
		...,
		description=('Identifier of parent ministry.'),
	)
	department_id: str = Field(
		...,
		description=('Identifier of parent department.'),
	)
	qdrant_id: str | None = Field(
		default=None,
		description=(
			'Unique identifier for the corresponding point '
			'in QdrantDB.'
		),
	)

	agency_name: str = Field(
		...,
		description=(
			'Agency name as listed on the eCitizen platform.'
		),
	)
	agency_description: str | None = Field(
		...,
		description=('Public agency description.'),
	)
	agency_description_summary: str | None = Field(
		default=None,
		description=(
			'Concise summary of the agency description, '
			'limited to 150 tokens.'
		),
	)
	logo_url: str | None = Field(
		...,
		description=('URL of agency logo image.'),
	)
	agency_url: str | None = Field(
		...,
		description=(
			'URL of agency page from the eCitizen platform.'
		),
	)
	observed_service_count: int | None = Field(
		...,
		description=('Number of services observed under the agency.'),
	)
	ministry_departments_agencies_url: str = Field(
		...,
		description=(
			'Ministry page URL scoped to '
			'department and agency via '
			'query parameters.'
		),
	)
