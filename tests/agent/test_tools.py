"""
This module tests agent tools, particularly the
corpus lookup tool and the FAQ list tool. It ensures
that the tools are functioning correctly and returning
expected results.
"""

import time

from agent.tools.corpus_lookup import corpus_lookup
from agent.tools.faq_list import form_faq_tool_response

# --- FAQ List Tool Tests ---


async def test_faq_list_tool():
	"""
	Test the FAQ List tool to ensure it returns a properly
	formatted string of FAQs.
	"""
	response = await form_faq_tool_response()
	assert isinstance(response, str)
	assert (
		response.startswith('Here are the current FAQs:')
		or response == 'No FAQs found in the database.'
	)


# --- Corpus Lookup Tool Tests ---


async def test_corpus_lookup_tool():
	"""
	Test the Corpus Lookup tool with a sample query and type filter.
	This test assumes that there are relevant entries in the corpus
	that match the query.
	"""
	query = 'services related to renewing a driving licence'
	type_filter = 'service'

	start_time = time.time()
	response = await corpus_lookup(query, type_filter)
	end_time = time.time()
	elapsed_time = end_time - start_time
	print(
		f'Corpus Lookup Tool executed in {elapsed_time:.2f} seconds.'
	)

	assert isinstance(response, str)
	# Expecting a non-empty response, either with
	# results or a message indicating no results/clarification needed
	assert len(response) > 0

	print('Corpus Lookup Tool Response:')
	print(response)
