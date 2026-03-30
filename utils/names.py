"""Name normalisation, fuzzy matching, and courtesy-owner extraction."""

import re
from collections.abc import Sequence

# Precompiled regex patterns
COURTESY_PATTERN = re.compile(r"^(.+?)\s*\(courtesy\s+(.+?)\)\s*$", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalise(name: str) -> str:
    """Return a normalised version of a name for comparison.

    Strips leading/trailing whitespace, collapses internal whitespace,
    and converts to lowercase.

    Args:
        name (str): Raw name string to normalise.

    Returns:
        str: Normalised lowercase string, or empty string when input is falsy.

    Example:
        >>> normalise("  Alice  Bob  ")
        'alice bob'
        >>> normalise("")
        ''
    """
    if not name:
        return ""
    return WHITESPACE_PATTERN.sub(" ", name.strip()).lower()


def find_best_match(name: str, candidates: Sequence[str]) -> str | None:
    """Return the best matching candidate using normalised comparison.

    Matching order:
    1. Exact normalised match
    2. Substring containment (either direction)

    Args:
        name (str): The name to look up.
        candidates (Sequence[str]): Pool of candidate strings to match against.

    Returns:
        str | None: The matching candidate in its original form, or ``None``
            when no match is found.

    Example:
        >>> find_best_match("kiran", ["Alice", "Kiran", "Bob"])
        'Kiran'
        >>> find_best_match("unknown", ["Alice"]) is None
        True
    """
    norm = normalise(name)
    if not norm:
        return None

    # Precompute normalised candidates to avoid redundant work in both passes
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
    """Extract the base game name and courtesy owner from a column header.

    Parses headers of the form ``"Game Name (courtesy PlayerName)"``
    into their constituent parts.

    Args:
        game_name (str): Raw column header from a game poll CSV.

    Returns:
        tuple[str, str | None]: ``(base_name, owner_name)`` when the courtesy
            pattern matches; ``(game_name, None)`` otherwise.

    Example:
        >>> extract_courtesy_owner("Kanban EV (courtesy Kiran)")
        ('Kanban EV', 'Kiran')
        >>> extract_courtesy_owner("Scythe")
        ('Scythe', None)
    """
    stripped = game_name.strip()
    match = COURTESY_PATTERN.match(stripped)

    if match:
        return match.group(1).strip(), match.group(2).strip()

    return stripped, None
