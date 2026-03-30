"""Cross-file validation for poll CSV inputs."""

import pandas as pd


def _get_name_set(df: pd.DataFrame) -> set[str]:
    """Return the set of player names from a poll DataFrame.

    Returns an empty set when the DataFrame is empty or lacks a Name column,
    so callers can safely perform set operations without additional guards.

    Args:
        df (pd.DataFrame): Poll DataFrame with an optional 'Name' column.

    Returns:
        set[str]: Player names as strings, or an empty set when unavailable.

    Example:
        >>> import pandas as pd
        >>> _get_name_set(pd.DataFrame({"Name": ["Alice", "Bob"]}))
        {'Alice', 'Bob'}
    """
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

    Checks that players who filled a game poll also appear in the timings
    and location polls. Players absent from either poll cannot be matched
    to a time slot or venue, so they will be silently excluded from
    scheduling.

    Args:
        heavy_df (pd.DataFrame): Heavy game poll DataFrame.
        medium_df (pd.DataFrame): Medium game poll DataFrame.
        timings_df (pd.DataFrame): Timings availability DataFrame.
        place_df (pd.DataFrame): Location preference DataFrame.

    Returns:
        list[str]: Human-readable warning messages; empty when all players
            appear in every poll.

    Example:
        >>> import pandas as pd
        >>> heavy = pd.DataFrame({"Name": ["Alice"]})
        >>> empty = pd.DataFrame({"Name": []})
        >>> warnings = validate_cross_files(heavy, empty, empty, empty)
        >>> any("timings" in w for w in warnings)
        True
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
