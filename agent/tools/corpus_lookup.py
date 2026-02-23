"""
This module contains the logic for the Corpus
Lookup tool, note the tool is called by the
agent via the 'agent.tools.dispatch' module
"""

import asyncio

from agent.retrieval.resolve import resolve_and_format_corpus_payload
from databases.qdrant.search import search_corpus
from exceptions.core import ApplicationException, ErrorContext
from openai_client.main import create_embedding
from schemas.corpus.qdrant import (
	CorpusItemType,
	CorpusPayload,
)

# --- Constants and utils ---

_EXPAND_SEARCH_THRESHOLD = 0.7
_CLARIFICATION_THRESHOLD = 0.5
_RECURSION_LIMIT = 1

# --- Main tool logic ---


def _resolve_search_type(item_type: str) -> CorpusItemType | None:
	"""
	Resolves the string representation of the item type
	to the corresponding CorpusItemType enum value.
	"""
	if item_type.lower() == 'any':
		return None  # No filter, search across all types
	try:
		return CorpusItemType(item_type.lower())
	except ValueError as e:
		raise ApplicationException(
			message=(
				f'Invalid type filter "{item_type}". '
				'Expected one of: ministry, department, '
				'agency, service.'
			),
			code='invalid_type_filter',
			context=ErrorContext(
				operation='corpus_lookup',
				component='agent.tools.corpus_lookup',
			),
		) from e


async def _corpus_search(
	query: str,
	type_filter: str,
	search_limit: int = 2,
	recursion_depth: int = 0,
) -> list[CorpusPayload] | None:
	"""
	Performs a corpus lookup using the provided
	query and type filter.
	"""
	search_type = _resolve_search_type(type_filter)
	query_embedding = await create_embedding(query)
	search_results = await search_corpus(
		query_vector=query_embedding,
		search_type=search_type,
		limit=search_limit,
	)

	# Check if results are below thresholds for retry or clarification
	if search_results:
		top_score = max(result.score for result in search_results)
		if top_score < _CLARIFICATION_THRESHOLD:
			# Ask for clarification from the user
			return None
		elif top_score < _EXPAND_SEARCH_THRESHOLD:
			# Expand the search by increasing the limit
			if recursion_depth < _RECURSION_LIMIT:
				return await _corpus_search(
					query=query,
					type_filter=type_filter,
					search_limit=3,
					recursion_depth=recursion_depth + 1,
				)
			else:
				# Recursion limit reached, return what we have
				return [result.payload for result in search_results]
		else:
			# Return the payloads of the search results
			return [result.payload for result in search_results]


async def corpus_lookup(
	query: str,
	type_filter: str,
) -> str:
	"""
	Performs a corpus lookup and returns a formatted string
	of the results or a message indicating no results found
	or asking for clarification.
	"""
	search_results = await _corpus_search(query, type_filter)
	if search_results is None:
		return (
			'Could not find relevant information. '
			'Could you please clarify your query?'
		)
	elif not search_results:
		return 'No relevant information found in the corpus.'
	else:
		# Resolve and format the payloads into a context string
		tasks = [
			resolve_and_format_corpus_payload(payload)
			for payload in search_results
		]
		formatted_results = await asyncio.gather(*tasks)
		return '\n\n'.join(formatted_results)
