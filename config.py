# Type aliases
PlayerId = str
GameId = str
SlotId = str
LocationId = str

# Constants
VOTE_MARKER = "\u2713"  # ✓ (Unicode U+2713)
EXCLUDED_COLUMNS = {"Name", "Total"}

# Internal scoring weights (not UI-exposed)
W_DEMAND = 0.40
W_DIVERSITY = 0.20
W_COVERAGE = 0.20
W_POPULARITY = 0.10
W_AVAILABILITY = 0.05
W_LOCATION = 0.05
