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
			'single-sentence English query for embedding-'
			'based retrieval.\n\n'
			'IMPORTANT: The query MUST always be written '
			'in clear, concise English. Even if the user '
			'asks in Swahili, Sheng, or another language, '
			'the assistant MUST translate the intent into '
			'English before constructing the query.\n\n'
			'The assistant MUST construct a single, '
			'precise sentence that captures exactly what '
			'the user is looking for.\n\n'
			'Do NOT include explanations, formatting, '
			'or multiple sentences. Do NOT include '
			'Markdown.\n\n'
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
						'One single English sentence describing '
						"the user's information need in a "
						'clear, embedding-friendly form.\n\n'
						"Example: 'services related to renewing "
						"a driving licence in Kenya'."
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
