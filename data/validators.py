"""Cross-file validation for poll CSV inputs."""

import pandas as pd


def _get_name_set(df: pd.DataFrame) -> set[str]:
    """Return cleaned player names from a DataFrame."""
    if df.empty or "Name" not in df.columns:
        return set()
    return set(df["Name"].astype(str))


def validate_cross_files(
    heavy_df: pd.DataFrame,
    medium_df: pd.DataFrame,
    timings_df: pd.DataFrame,
    place_df: pd.DataFrame,
) -> list[str]:
    """Validate player coverage across all CSV inputs.

    Checks that players who filled a game poll also appear in
    the timings and location polls.

    Returns:
        List of validation warnings.
    """
    warnings: list[str] = []

    game_players = _get_name_set(heavy_df) | _get_name_set(medium_df)
    timing_players = _get_name_set(timings_df)
    place_players = _get_name_set(place_df)

    missing_timing = sorted(game_players - timing_players)
    if missing_timing:
        warnings.append(
            f"{', '.join(missing_timing)} filled the game poll but didn't fill "
            "the timings poll, so we can't match them to a time slot yet."
        )

    missing_place = sorted(game_players - place_players)
    if missing_place:
        warnings.append(
            f"{', '.join(missing_place)} filled the game poll but didn't fill "
            "the location poll, so we can't assign them a venue yet."
        )

    return warnings
