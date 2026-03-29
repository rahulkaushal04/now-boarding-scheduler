from __future__ import annotations

import re
from typing import Sequence

# Precompiled regex patterns
COURTESY_PATTERN = re.compile(r"^(.+?)\s*\(courtesy\s+(.+?)\)\s*$", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalise(name: str) -> str:
    """Return a normalised version of a name.

    Strips leading/trailing whitespace, collapses internal whitespace,
    and converts to lowercase.
    """
    if not name:
        return ""
    return WHITESPACE_PATTERN.sub(" ", name.strip()).lower()


def find_best_match(name: str, candidates: Sequence[str]) -> str | None:
    """Return the best matching candidate using normalised comparison.

    Matching order:
    1. Exact normalised match
    2. Substring containment (either direction)
    """
    norm = normalise(name)
    if not norm:
        return None

    # Precompute normalised candidates
    normalised_candidates = [(c, normalise(c)) for c in candidates]

    # Exact match
    for original, cn in normalised_candidates:
        if cn == norm:
            return original

    # Substring match
    for original, cn in normalised_candidates:
        if norm in cn or cn in norm:
            return original

    return None


def extract_courtesy_owner(game_name: str) -> tuple[str, str | None]:
    """Extract base name and courtesy owner.

    Expected format: "Game Name (courtesy PlayerName)".

    Returns:
        tuple[str, str | None]: (base_name, owner_name) or (game_name, None)
    """
    stripped = game_name.strip()
    match = COURTESY_PATTERN.match(stripped)

    if match:
        return match.group(1).strip(), match.group(2).strip()

    return stripped, None
