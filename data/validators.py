from __future__ import annotations

from typing import List, Set

import pandas as pd

from utils.names import extract_courtesy_owner, normalise

EXCLUDED_COLUMNS = {"Name", "Total"}


def _get_name_set(df: pd.DataFrame) -> Set[str]:
    """Return a set of cleaned names from a DataFrame."""
    if df.empty or "Name" not in df.columns:
        return set()
    return set(df["Name"].astype(str))


def _get_game_columns(df: pd.DataFrame) -> Set[str]:
    """Return non-excluded column names from a DataFrame."""
    if df.empty:
        return set()
    return {c for c in df.columns if c not in EXCLUDED_COLUMNS}


def validate_cross_files(
    heavy_df: pd.DataFrame,
    medium_df: pd.DataFrame,
    timings_df: pd.DataFrame,
    place_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
) -> List[str]:
    """Perform cross-file validation across all CSV inputs.

    Returns:
        list[str]: Validation warnings/errors.
    """
    warnings: List[str] = []

    # Collect player names
    game_players = _get_name_set(heavy_df) | _get_name_set(medium_df)
    timing_players = _get_name_set(timings_df)
    place_players = _get_name_set(place_df)

    # Missing in timings
    for player in sorted(game_players - timing_players):
        warnings.append(
            f"Player '{player}' voted on games but not on timings — excluded from overlaps"
        )

    # Missing in place
    for player in sorted(game_players - place_players):
        warnings.append(
            f"Player '{player}' voted on games but not on locations — excluded from overlaps"
        )

    # Metadata coverage
    if not metadata_df.empty and "Name" in metadata_df.columns:
        metadata_names = {normalise(n) for n in metadata_df["Name"].astype(str)}

        all_game_cols = _get_game_columns(heavy_df) | _get_game_columns(medium_df)

        for raw_name in sorted(all_game_cols):
            base, _ = extract_courtesy_owner(raw_name)
            if normalise(base) not in metadata_names:
                warnings.append(f"Game '{base}' missing from metadata CSV")

    return warnings


def normalise_name(name: str) -> str:
    """Return a normalised name (alias for utils.names.normalise)."""
    return normalise(name)
