"""
This module contains logic related to resolving and
retrieving relevant metadata and information from the
corpus for a given search result form the Corpus Lookup tool.
"""

from agent.retrieval.format import (
	form_agency_context,
	form_department_context,
	form_ministry_context,
	form_service_context,
)
from databases.mongodb.main import MongoDBCollection, get_collection
from exceptions.core import ApplicationException, ErrorContext
from schemas.corpus.agencies import AgencyEntry
from schemas.corpus.departments import DepartmentEntry
from schemas.corpus.ministries import MinistryEntry
from schemas.corpus.qdrant import CorpusItemType, CorpusPayload
from schemas.corpus.services import ServiceEntry

# --- Utilities ---

_item_type_to_collection = {
	CorpusItemType.MINISTRY: MongoDBCollection.MINISTRIES,
	CorpusItemType.DEPARTMENT: MongoDBCollection.DEPARTMENTS,
	CorpusItemType.AGENCY: MongoDBCollection.AGENCIES,
	CorpusItemType.SERVICE: MongoDBCollection.SERVICES,
}

# --- Main resolution logic ---


async def resolve_and_format_corpus_payload(
	payload: CorpusPayload,
) -> str:
	"""
	Resolves the corpus payload to retrieve relevant metadata
	and formats it into a context string for the agent.
	"""

	collection_name = _item_type_to_collection.get(payload.type)
	if not collection_name:
		raise ApplicationException(
			message=(
				f'Failed to resolve collection '
				f'for item type {payload.type}.'
			),
			code='collection_resolution_failed',
			context=ErrorContext(
				operation='resolve_corpus_payload',
				component='agent.retrieval.resolve',
			),
		)

	collection = await get_collection(collection_name)

	# Convert the MongoDB document to the appropriate schema entry
	if payload.type == CorpusItemType.MINISTRY:
		document = await collection.find_one(
			{'ministry_id': payload.entity_id}, {'_id': 0}
		)
		ministry_entry = MinistryEntry.model_validate(document)
		return form_ministry_context(ministry_entry)
	elif payload.type == CorpusItemType.DEPARTMENT:
		document = await collection.find_one(
			{'department_id': payload.entity_id}, {'_id': 0}
		)
		department_entry = DepartmentEntry.model_validate(document)
		return await form_department_context(department_entry)
	elif payload.type == CorpusItemType.AGENCY:
		document = await collection.find_one(
			{'agency_id': payload.entity_id}, {'_id': 0}
		)
		agency_entry = AgencyEntry.model_validate(document)
		return await form_agency_context(agency_entry)
	elif payload.type == CorpusItemType.SERVICE:
		document = await collection.find_one(
			{'service_id': payload.entity_id}, {'_id': 0}
		)
		service_entry = ServiceEntry.model_validate(document)
		return await form_service_context(service_entry)

	# If we reach here, it means the type was not recognized
	raise ApplicationException(
		message=(
			f'Unrecognized item type '
			f'{payload.type} in corpus payload.'
		),
		code='unrecognized_item_type',
		context=ErrorContext(
			operation='resolve_corpus_payload',
			component='agent.retrieval.resolve',
		),
	)
