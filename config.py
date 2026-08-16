"""Global configuration: CSV parsing constants and display-ranking weights."""

VOTE_MARKER: str = "✓"  # ✓ (Unicode U+2713)
EXCLUDED_COLUMNS: frozenset[str] = frozenset({"Name", "Total"})

# Display-only ranking weights, consumed solely by engine/scorer.py to order
# candidates for the UI (e.g. picking the "best" near-miss suggestion per
# unscheduled game). They do NOT influence which sessions actually get
# scheduled — that decision is made exclusively by the exact MILP in
# engine/optimizer.py, which never reads these constants.
W_DEMAND: float = 0.30
W_DIVERSITY: float = 0.10
W_COVERAGE: float = 0.30
W_POPULARITY: float = 0.10
W_AVAILABILITY: float = 0.15
W_LOCATION: float = 0.05
