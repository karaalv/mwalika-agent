"""
This module contains logic for formatting data
from the retrieval process into a format suitable for
the agent's consumption, primarily adding relevant metadata
and context to the retrieved information to enhance the agent's
understanding and response generation.
"""

from textwrap import dedent

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.corpus.agencies import AgencyEntry
from schemas.corpus.departments import DepartmentEntry
from schemas.corpus.ministries import MinistryEntry
from schemas.corpus.services import ServiceEntry

# --- Utilities ---


async def _get_ministry_entry(entity_id: str) -> MinistryEntry | None:
	collection = get_collection(MongoDBCollection.MINISTRIES)
	document = await collection.find_one(
		{'ministry_id': entity_id}, {'_id': 0}
	)
	return (
		MinistryEntry.model_validate(document) if document else None
	)


async def _get_department_entry(
	entity_id: str,
) -> DepartmentEntry | None:
	collection = get_collection(MongoDBCollection.DEPARTMENTS)
	document = await collection.find_one(
		{'department_id': entity_id}, {'_id': 0}
	)
	return (
		DepartmentEntry.model_validate(document) if document else None
	)


async def _get_agency_entry(entity_id: str) -> AgencyEntry | None:
	collection = get_collection(MongoDBCollection.AGENCIES)
	document = await collection.find_one(
		{'agency_id': entity_id}, {'_id': 0}
	)
	return AgencyEntry.model_validate(document) if document else None


# --- Context formatting logic ---


def form_ministry_context(
	ministry_entry: MinistryEntry,
) -> str:
	# Form ministry-specific context
	description = (
		ministry_entry.ministry_description
		or 'No description available.'
	)
	return dedent(f"""
        --- Ministry Information ---
        Ministry Name: {ministry_entry.ministry_name}
        Description: {description}
        eCitizen Link: {ministry_entry.ministry_url}
    """).strip()


async def form_department_context(
	department_entry: DepartmentEntry,
) -> str:
	# Get parent hierarchy context
	parent_ministry = await _get_ministry_entry(
		department_entry.ministry_id
	)
	ministry_context = 'No ministry information available.'
	if parent_ministry:
		ministry_context = form_ministry_context(parent_ministry)

	# Form department-specific context
	return (
		ministry_context
		+ '\n\n'
		+ dedent(f"""
        --- Department Information ---
        Department Name: {department_entry.department_name}
        eCitizen Link: {department_entry.ministry_departments_url}
    """).strip()
	)


async def form_agency_context(agency_entry: AgencyEntry) -> str:
	# Get parent hierarchy context
	parent_department = await _get_department_entry(
		agency_entry.department_id
	)
	department_context = 'No department information available.'
	if parent_department:
		department_context = await form_department_context(
			parent_department
		)

	# Form agency-specific context
	description = (
		agency_entry.agency_description or 'No description available.'
	)
	return (
		department_context
		+ '\n\n'
		+ dedent(f"""
        --- Agency Information ---
        Agency Name: {agency_entry.agency_name}
        Description: {description}
        eCitizen Link:
		{agency_entry.ministry_departments_agencies_url}
        Logo URL: {agency_entry.logo_url}
        Agency Page URL: {agency_entry.agency_url}
    """).strip()
	)


async def form_service_context(service_entry: ServiceEntry) -> str:
	# Get parent hierarchy context
	parent_agency = await _get_agency_entry(service_entry.agency_id)
	agency_context = 'No agency information available.'
	if parent_agency:
		agency_context = await form_agency_context(parent_agency)

	# Form service-specific context
	description = (
		service_entry.service_description
		or 'No description available.'
	)
	return (
		agency_context
		+ '\n\n'
		+ dedent(f"""
        --- Service Information ---
        Service Name: {service_entry.service_name}
        Description: {description}
        eCitizen Link: {service_entry.service_url}
    """).strip()
	)
