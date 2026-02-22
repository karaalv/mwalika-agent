"""
This module contains logic for updating user information
in the Mwalika Agent system, specifically for updating
usage statistics and other relevant user data when they interact
with the system.
"""

from databases.mongodb.main import MongoDBCollection, get_collection
from shared.time import get_timestamp


async def increment_user_requests(user_id: str) -> None:
	"""
	Increments the number of requests made by the user today
	and updates the timestamp of their last request.
	"""
	usage_stats_collection = await get_collection(
		MongoDBCollection.USER_USAGE_STATS
	)
	await usage_stats_collection.update_one(
		{'user_id': user_id},
		{
			'$inc': {'requests_today': 1},
			'$set': {'last_request_timestamp': get_timestamp()},
		},
	)


async def increment_user_agent_input_tokens(
	user_id: str, tokens: int
) -> None:
	"""
	Increments the total number of input tokens
	sent to agents by the user and updates the count
	for today.
	"""
	usage_stats_collection = await get_collection(
		MongoDBCollection.USER_USAGE_STATS
	)
	await usage_stats_collection.update_one(
		{'user_id': user_id},
		{
			'$inc': {
				'agent_input_tokens': tokens,
				'agent_input_tokens_today': tokens,
			},
			'$set': {'last_request_timestamp': get_timestamp()},
		},
	)
