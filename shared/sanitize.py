"""
This module contains logic for managing
sanitization of user inputs and other data before
processing, to ensure security and data integrity.
"""

import re
import unicodedata

from security.config.agent import (
	MAX_INPUT_LENGTH,
	MAX_SINGLE_INPUT_TOKEN_LENGTH,
)

EMAIL_RE = re.compile(
	r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
	re.IGNORECASE,
)

PHONE_RE = re.compile(
	r'(?:\+?\d{1,3}[\s\-()]*)?(?:\d[\s\-()]*){7,14}'
)

CARD_RE = re.compile(r'\b(?:\d[ -]*?){13,19}\b')

ID_NUMBER_RE = re.compile(r'\b\d{7,12}\b')

URL_RE = re.compile(
	r'\bhttps?://[^\s]+|\bwww\.[^\s]+\b',
	re.IGNORECASE,
)

IPV4_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

WHITESPACE_RE = re.compile(r'\s+')
LONG_SPACE_RE = re.compile(r'[ \t]{2,}')
LONG_TOKEN_RE = re.compile(
	rf'\b\S{{{MAX_SINGLE_INPUT_TOKEN_LENGTH},}}\b'
)


def _strip_control_chars(text: str) -> str:
	result: list[str] = []

	for ch in text:
		cat = unicodedata.category(ch)

		if ch in ('\n', '\t', ' '):
			result.append(ch)
			continue

		if cat.startswith('C'):
			continue

		result.append(ch)

	return ''.join(result)


def _normalise_whitespace(text: str) -> str:
	text = text.replace('\r\n', '\n').replace('\r', '\n')
	text = LONG_SPACE_RE.sub(' ', text)
	return text.strip()


def _redact_pii(text: str) -> str:
	text = EMAIL_RE.sub('[redacted-email]', text)
	text = URL_RE.sub('[redacted-url]', text)
	text = IPV4_RE.sub('[redacted-ip]', text)
	text = CARD_RE.sub('[redacted-card]', text)
	text = PHONE_RE.sub('[redacted-phone]', text)
	text = ID_NUMBER_RE.sub('[redacted-number]', text)
	return text


def _clean_noise(text: str) -> str:
	text = LONG_TOKEN_RE.sub('[redacted-long-token]', text)
	return text


def _looks_like_nonsense(text: str) -> bool:
	if not text:
		return True

	compact = WHITESPACE_RE.sub('', text)

	if not compact:
		return True

	alpha = sum(ch.isalpha() for ch in compact)
	digits = sum(ch.isdigit() for ch in compact)
	alnum = alpha + digits

	if len(compact) > 20 and alnum == 0:
		return True

	if len(compact) >= 20:
		weird_ratio = sum(
			not ch.isalnum() and ch not in ".,?!:;'-_/()"
			for ch in compact
		) / len(compact)

		if weird_ratio > 0.45:
			return True

	if len(compact) >= 24 and alpha > 0:
		vowels = sum(ch.lower() in 'aeiou' for ch in compact)

		if vowels / max(alpha, 1) < 0.08:
			return True

	return False


def scrub_string(value: str) -> str:
	"""
	Sanitizes the input value by normalizing
	unicode characters, stripping control characters,
	redacting personally identifiable information (PII),
	and normalizing whitespace. If the input is not a string,
	it is returned as-is. If the sanitized result looks like
	nonsense (e.g., very long tokens, low vowel ratio), it is
	replaced with a redacted placeholder.
	"""

	if not isinstance(value, str):
		return '[redacted-non-string-input]'

	text = unicodedata.normalize('NFKC', value)

	text = _strip_control_chars(text)
	text = _normalise_whitespace(text)

	if not text:
		return ''

	text = text[:MAX_INPUT_LENGTH]

	text = _clean_noise(text)
	text = _redact_pii(text)

	text = _normalise_whitespace(text)

	if _looks_like_nonsense(text):
		return '[redacted-noisy-input]'

	return text
