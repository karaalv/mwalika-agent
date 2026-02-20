"""
This module contains the logic for
the FAQ List tool, note the tool is
called by the agent via the 'agent.tools.dispatch'
module
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.corpus.faqs import FAQEntry


async def get_faq_list() -> list[FAQEntry]:
	"""
	Retrieves the list of FAQs from the MongoDB collection.
	"""
	faq_collection = await get_collection(MongoDBCollection.FAQS)
	faqs = await faq_collection.find().to_list()
	return [FAQEntry.model_validate(faq) for faq in faqs]


async def form_faq_tool_response() -> str:
	"""
	Forms a response string containing the list
	of FAQs for the agent to use.
	"""
	faq_entries = await get_faq_list()
	if not faq_entries:
		return 'No FAQs found in the database.'

	response = 'Here are the current FAQs:\n\n'
	for faq in faq_entries:
		response += f'Q: {faq.question}\nA: {faq.answer}\n\n'

	return response.strip()
