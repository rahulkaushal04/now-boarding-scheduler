"""Global configuration: constants and scoring weights."""

VOTE_MARKER: str = "\u2713"  # ✓ (Unicode U+2713)
EXCLUDED_COLUMNS: frozenset[str] = frozenset({"Name", "Total"})

# Internal scoring weights (not UI-exposed)
W_DEMAND: float = 0.30
W_DIVERSITY: float = 0.10
W_COVERAGE: float = 0.30
W_POPULARITY: float = 0.10
W_AVAILABILITY: float = 0.15
W_LOCATION: float = 0.05
