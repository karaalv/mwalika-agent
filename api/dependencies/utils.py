"""
This module defines utilities used in the dependencies of
the API system, this primarily includes utilities for checking
authentication and authorization, such as blocked tokens or
IPs, as well as other helper functions used across multiple
dependencies.
"""

from fastapi import HTTPException, status

from security.lifecycle import (
	is_at_blocked,
	is_ip_blocked,
	is_rt_blocked,
	is_user_blocked,
	update_latest_at_request,
	update_latest_ip_request,
	update_latest_rt_request,
	update_latest_user_request,
)

# --- Block status check utilities ---


async def check_ip_blocked(ip_address: str) -> None:
	"""
	First records new request for the given IP address, then
	checks if the IP address is blocked and raises
	HTTPException if so.
	"""
	if not ip_address.strip():
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail='Invalid IP address',
		)

	await update_latest_ip_request(ip_address)
	blocked_entity = await is_ip_blocked(ip_address)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


async def check_rt_blocked(token_id: str) -> None:
	"""
	First records new request for the given refresh token ID, then
	checks if the refresh token ID is blocked and raises
	HTTPException if so.
	"""
	if not token_id.strip():
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail='Invalid token ID',
		)

	await update_latest_rt_request(token_id)
	blocked_entity = await is_rt_blocked(token_id)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


async def check_at_blocked(token_id: str) -> None:
	"""
	First records new request for the given access token ID, then
	checks if the access token ID is blocked and raises
	HTTPException if so.
	"""
	if not token_id.strip():
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail='Invalid token ID',
		)

	await update_latest_at_request(token_id)
	blocked_entity = await is_at_blocked(token_id)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


async def check_user_blocked(user_id: str) -> None:
	"""
	First records new request for the given user ID, then
	checks if the user ID is blocked and raises HTTPException
	if so.
	"""
	if not user_id.strip():
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail='Invalid user ID',
		)

	await update_latest_user_request(user_id)
	blocked_entity = await is_user_blocked(user_id)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)
