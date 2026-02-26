"""
This module contains guards for user routes in the
Mwalika Agent system. These guards are used to protect
certain API endpoints by enforcing the security policies
defined in the observers, such as blocking users, IP addresses, or
tokens that have been flagged for suspicious behavior or abuse.
"""

from api.guards.users.checks import (
	check_at_generation_user,
	check_claim_cookie_at,
	check_claim_cookie_ip,
	check_claim_cookie_user,
	check_rt_generation_ip,
)


async def guard_claim_cookie_generation(
	ip_address: str,
	user_id: str,
	token_id: str,
) -> None:
	"""
	Guard function that checks if the given IP address, user ID, or
	access token ID has been flagged for suspicious behavior or abuse
	by the respective observers when generating a claim cookie, and
	raises HTTPException if so.
	"""
	await check_claim_cookie_ip(ip_address)
	await check_claim_cookie_at(token_id)
	await check_claim_cookie_user(user_id)


async def guard_rt_generation(
	ip_address: str,
) -> None:
	"""
	Guard function that checks if the given IP address has been
	flagged for suspicious behavior or abuse by the IP observer when
	generating a refresh token, and raises HTTPException if so.
	"""
	await check_rt_generation_ip(ip_address)


async def guard_at_generation(
	user_id: str,
) -> None:
	"""
	Guard function that checks if the given user ID has been
	flagged for suspicious behavior or abuse by the user observer
	when generating an access token, and raises HTTPException if so.
	"""
	await check_at_generation_user(user_id)
