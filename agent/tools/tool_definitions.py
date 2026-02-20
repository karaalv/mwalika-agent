"""
This module contains tool definitions
for the Mwalika Agent system.
"""

from openai.types.responses import ToolParam

from schemas.corpus.qdrant import CorpusItemType

TOOL_DEFINITIONS: list[ToolParam] = [
	# FAQ List Tool
	{
		'type': 'function',
		'name': 'faq_list',
		'description': (
			'Return all eCitizen FAQ questions and answers. '
			'Use for general lookup of common FAQs.'
		),
		'strict': True,
		'parameters': {
			'type': 'object',
			'properties': {},
			'required': [],
			'additionalProperties': False,
		},
	},
	# Corpus Search Tool
	{
		'type': 'function',
		'name': 'corpus_lookup',
		'description': (
			'Search the structured corpus (ministries, '
			'departments, agencies, services) using a '
			'single-sentence query for embedding-based '
			'retrieval. The assistant MUST construct a '
			'concise query sentence that captures exactly '
			'what the user is looking for.\n\n'
			'If unsure which corpus type is most relevant, '
			"use 'any' to search across all corpus types."
		),
		'strict': True,
		'parameters': {
			'type': 'object',
			'properties': {
				'query': {
					'type': 'string',
					'description': (
						"One sentence describing the user's "
						'information need in a queryable form. '
						"Example: 'services related to renewing "
						"a driving licence'."
					),
					'minLength': 3,
				},
				'type_filter': {
					'type': 'string',
					'description': (
						'Corpus type to filter search results. '
						'Use one of: ministry, department, '
						"agency, service. Use 'any' to search "
						'across all types if unsure.'
					),
					'enum': (
						[t.value for t in CorpusItemType] + ['any']
					),
				},
			},
			'required': ['query', 'type_filter'],
			'additionalProperties': False,
		},
	},
]
