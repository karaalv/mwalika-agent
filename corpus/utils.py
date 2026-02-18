"""
This module contains utility functions used
specifically for processing the Mwalika Corpus
and not in the rest of the codebase.
"""

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> list[dict[str, Any]]:
	with path.open('r', encoding='utf-8') as f:
		return json.load(f)
