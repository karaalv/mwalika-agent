"""
This module contains tests for the user feedback API
routes, specifically testing the feedback submission
functionality.
"""

from httpx import AsyncClient

from api.utils.tokens import generate_access_token
from databases.mongodb.main import MongoDBCollection, get_collection
from schemas.users.core import LanguagePreference
from schemas.users.feedback import (
	IntendedServiceCategory,
	PromptSource,
	ServiceMatchedQuality,
	WhatHelped,
	WhatWentWrong,
)
from shared.ids import generate_uuid_str
from users.service.creation import create_anonymous_user

# --- Test helpers ---


async def _clear_feedback_collection():
	"""
	Helper function to clear the feedback collection in the database
	before running tests to ensure a clean state.
	"""
	feedback_collection = get_collection(
		MongoDBCollection.USER_FEEDBACK
	)
	await feedback_collection.delete_many({})


async def _clear_users_collection():
	"""
	Helper function to clear the users collection in the database
	before running tests to ensure a clean state.
	"""
	users_collection = get_collection(MongoDBCollection.USERS)
	await users_collection.delete_many({})


# --- Test cases for feedback submission ---


async def test_submit_feedback_success(http_client: AsyncClient):
	"""
	Test the /feedback endpoint to ensure it accepts valid feedback
	submissions and stores them correctly in the database.
	"""
	# Create a test user and generate an access
	# token for authentication
	test_user = await create_anonymous_user(
		user_id=generate_uuid_str()
	)
	token_res = generate_access_token(user_id=test_user.user_id)
	access_token = token_res.token

	# Define a sample feedback submission payload
	feedback_payload = {
		'session_id': generate_uuid_str(),
		'memory_id': generate_uuid_str(),
		'language_preference': LanguagePreference.ENGLISH,
		'prompt_source': PromptSource.AGENT,
		'helpful': True,
		'intended_service_category': IntendedServiceCategory.OTHER,
		'service_matched_quality': ServiceMatchedQuality.YES,
		'what_helped': [WhatHelped.CLARITY, WhatHelped.EASE_OF_USE],
		'what_went_wrong': [WhatWentWrong.TOO_SLOW],
		'comments': 'The service was good but could be improved.',
	}

	# Send the feedback submission request with the access token
	response = await http_client.post(
		'/users/feedback',
		json=feedback_payload,
		headers={'Authorization': f'Bearer {access_token}'},
	)

	print('Response:', response.text)

	# Assert that the response indicates success
	assert response.status_code == 201

	# Clear the feedback collection after the test
	await _clear_feedback_collection()
	await _clear_users_collection()
