"""
This module contains tests for HTTP user routes in
the Mwalika Agent API.
"""

from httpx import AsyncClient

from api.utils.tokens import (
	generate_access_token,
	generate_claim_token,
	generate_frontend_token,
	generate_refresh_token,
)
from schemas.api.responses import HttpApiResponse
from schemas.security.ratelimit import (
	ResourcePolicyIdentifierType,
	ResourcePolicyType,
)
from security.config.observers import MAX_PER_MINUTE_REQUESTS_PER_RT
from security.ratelimit.policies import POLICY_LIMITER_CONFIG_MAPPING
from shared.ids import generate_uuid_str
from tests.utils.generate_data import gen_test_ip

# --- Test cases for user routes ---


# Route functionality tests


async def test_get_refresh_token_success(http_client: AsyncClient):
	"""
	Test the /mwalika-rt endpoint to ensure it returns
	a valid refresh token when accessed with the correct
	frontend header and rate limits.
	"""

	# Generate a frontend token for authentication
	frontend_token = generate_frontend_token()

	# Make a request to the refresh token
	# endpoint with the frontend token
	response = await http_client.get(
		'/users/mwalika-rt',
		headers={'X-Mwalika': frontend_token},
	)

	assert response.status_code == 200

	# Check cookies for the refresh token
	assert 'mwalika_rt' in response.cookies
	assert response.cookies['mwalika_rt'] is not None


async def test_get_refresh_token_failure_no_frontend_header(
	http_client: AsyncClient,
):
	"""
	Test the /mwalika-rt endpoint to ensure it fails
	when the required frontend header is missing.
	"""

	# Make a request to the refresh token endpoint
	# without the frontend token
	response = await http_client.get('/users/mwalika-rt')

	assert response.status_code == 422


async def test_get_access_token_success(http_client: AsyncClient):
	"""
	Test the /mwalika-at endpoint to ensure it returns
	a valid access token when accessed with a valid refresh
	token.
	"""

	# First, get a refresh token
	refresh_token = generate_refresh_token()
	http_client.cookies.set('mwalika_rt', refresh_token)

	response = await http_client.get(
		'/users/mwalika-at',
	)

	assert response.status_code == 200
	data = response.json()
	http_api_response = HttpApiResponse.model_validate(data)
	assert http_api_response.meta.success is True
	data = http_api_response.data
	assert data is not None
	assert 'access_token' in data

	http_client.cookies.clear()


async def test_get_access_token_failure_no_refresh_token(
	http_client: AsyncClient,
):
	"""
	Test the /mwalika-at endpoint to ensure it fails
	when the required refresh token cookie is missing.
	"""

	# Make a request to the access token endpoint
	# without the refresh token cookie
	response = await http_client.get('/users/mwalika-at')

	assert response.status_code == 401


async def test_post_claim_cookie_success(http_client: AsyncClient):
	"""
	Test the /claim-user-cookie endpoint to ensure it allows
	a client to claim a user ID with a valid claim token.
	"""

	# Generate a claim token for testing
	test_user_id = generate_uuid_str()
	claim_token = generate_claim_token(user_id=test_user_id)
	access_token = generate_access_token(user_id=test_user_id)

	# Make a request to the claim cookie endpoint
	response = await http_client.post(
		'/users/claim-user-cookie',
		json={
			'claim_token': claim_token,
			'user_id': test_user_id,
		},
		headers={'Authorization': f'Bearer {access_token}'},
	)

	assert response.status_code == 200

	# Check cookies for the user ID and refresh token
	assert 'user_id' in response.cookies
	assert response.cookies['user_id'] == test_user_id
	assert 'mwalika_rt' in response.cookies
	assert response.cookies['mwalika_rt'] is not None


async def test_post_claim_cookie_failure_invalid_access_token(
	http_client: AsyncClient,
):
	"""
	Test the /claim-user-cookie endpoint to ensure it fails
	when an invalid access token is provided.
	"""

	# Generate a claim token for testing
	test_user_id = generate_uuid_str()
	claim_token = generate_claim_token(user_id=test_user_id)

	# Make a request to the claim cookie endpoint
	# with an invalid access token
	response = await http_client.post(
		'/users/claim-user-cookie',
		json={
			'claim_token': claim_token,
			'user_id': test_user_id,
		},
		headers={'Authorization': 'Bearer invalid_access_token'},
	)

	assert response.status_code == 401


# Route security tests


async def test_get_refresh_token_blocked_ip(http_client: AsyncClient):
	"""
	Test the /mwalika-rt endpoint to ensure it blocks requests
	from an IP address that has been flagged for suspicious behavior
	by the IP observer.
	"""

	# Generate a test IP address and block it in the IP observer
	test_ip = gen_test_ip()
	frontend_token = generate_frontend_token()

	# Trigger rate limit to block the IP
	policy = POLICY_LIMITER_CONFIG_MAPPING[
		ResourcePolicyType.REFRESH_TOKEN
	][ResourcePolicyIdentifierType.IP]
	response = None
	for _ in range(policy.max_rate + 1):
		response = await http_client.get(
			'/users/mwalika-rt',
			headers={
				'X-Forwarded-For': test_ip,
				'X-Mwalika': frontend_token,
			},
		)
		if response.status_code == 429:
			break

	assert response is not None
	assert response.status_code == 429


async def test_get_access_token_blocked(
	http_client: AsyncClient,
):
	"""
	Test the /mwalika-at endpoint to ensure it blocks requests
	from a user ID that has been flagged for suspicious behavior
	by the user observer.
	"""

	# Generate a test user ID and block it in the user observer
	test_user_id = generate_uuid_str()
	refresh_token = generate_refresh_token(user_id=test_user_id)
	http_client.cookies.set('mwalika_rt', refresh_token)

	# Trigger rate limit to block the refresh token
	response = None
	for _ in range(MAX_PER_MINUTE_REQUESTS_PER_RT + 1):
		response = await http_client.get('/users/mwalika-at')
		if response.status_code == 403:
			break

	assert response is not None
	assert response.status_code == 403

	http_client.cookies.clear()
