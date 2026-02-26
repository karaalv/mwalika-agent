"""
This module contains checks used in the guards for
user routes in the Mwalika Agent system. These checks are used to
enforce the security policies defined in the observers, such as
blocking users, IP addresses, or tokens that have been flagged for
suspicious behavior or abuse.
"""

from fastapi import HTTPException, status

from security.lifecycle import (
	get_ip_observer,
	get_token_observer,
	get_user_observer,
)

# --- Refresh token generation checks ---


async def check_rt_generation_ip(ip_address: str) -> None:
	"""
	Checks if the given IP address has been flagged for suspicious
	behavior or abuse by the IP observer, and raises HTTPException
	if so.
	"""
	ip_observer = get_ip_observer()
	blocked_entity = await ip_observer.add_rt_generation(ip_address)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


# --- Access token generation checks ---


async def check_at_generation_user(user_id: str) -> None:
	"""
	Checks if the given user ID has been flagged for suspicious
	behavior or abuse by the user observer, and raises HTTPException
	if so.
	"""
	user_observer = get_user_observer()
	blocked_entity = await user_observer.add_at_generation(user_id)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


# --- Claim cookie checks ---


async def check_claim_cookie_ip(ip_address: str) -> None:
	"""
	Checks if the given IP address has been flagged for suspicious
	behavior or abuse by the IP observer, and raises HTTPException
	if so.
	"""
	ip_observer = get_ip_observer()
	blocked_entity = await ip_observer.add_claim_cookie_generation(
		ip_address
	)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


async def check_claim_cookie_user(user_id: str) -> None:
	"""
	Checks if the given user ID has been flagged for suspicious
	behavior or abuse by the user observer, and raises HTTPException
	if so.
	"""
	user_observer = get_user_observer()
	blocked_entity = await user_observer.add_claim_cookie_generation(
		user_id
	)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)


async def check_claim_cookie_at(token_id: str) -> None:
	"""
	Checks if the given access token ID has been flagged for
	suspicious behavior or abuse by the token observer, and raises
	HTTPException if so.
	"""
	token_observer = get_token_observer()
	blocked_entity = (
		await token_observer.add_at_claim_cookie_generation(
			token_id,
		)
	)
	if blocked_entity:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=blocked_entity.reason,
		)
