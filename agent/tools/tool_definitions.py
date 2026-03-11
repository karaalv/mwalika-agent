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
			'departments, agencies, services) using an '
			'English query for embedding-based retrieval.\n\n'
			'IMPORTANT: The query MUST always be written '
			'in clear, concise English.\n\n'
			'IMPORTANT: The type_filter MUST also use the '
			'English enum values provided by this tool.\n\n'
			'Even if the user asks in Swahili, Sheng, or a '
			'mixed language, the assistant MUST first '
			'translate the user intent into English before '
			'constructing the tool arguments.\n\n'
			'The assistant must use English only for both:'
			'\n- query'
			'\n- type_filter\n\n'
			'The final user-facing response may still be in '
			'the user’s preferred language.\n\n'
			'Construct a single, precise, embedding-friendly '
			'sentence that captures exactly what the user is '
			'looking for.\n\n'
			'Do NOT include explanations, formatting, '
			'or multiple sentences. Do NOT include Markdown.'
		),
		'strict': True,
		'parameters': {
			'type': 'object',
			'properties': {
				'query': {
					'type': 'string',
					'description': (
						'One single English sentence describing the '
						"user's information need in a clear, "
						'concise, embedding-friendly form.\n\n'
						'This field MUST be in English only,  '
						'even if the user asked the question in '
						'Swahili, Sheng, or a mixed language.\n\n'
						"Example: 'services related to renewing a "
						"driving licence in Kenya'."
					),
					'minLength': 3,
				},
				'type_filter': {
					'type': 'string',
					'description': (
						'Corpus type to filter search results.\n\n'
						'This field MUST use the English enum values '
						'provided by this tool only.\n\n'
						'Use one of: ministry, department, agency, '
						"service. Use 'any' to search across "
						'all types if unsure.\n\n'
						'Do NOT translate these values into Swahili.'
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
