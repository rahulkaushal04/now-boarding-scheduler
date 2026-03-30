"""CSV loading and parsing for game polls, timings, places, and metadata."""

from typing import IO, Any

import pandas as pd

from config import EXCLUDED_COLUMNS, VOTE_MARKER


def _strip_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows and columns labeled 'Total'."""
    df = df.drop(
        columns=[c for c in df.columns if str(c).strip() == "Total"],
        errors="ignore",
    )
    if "Name" in df.columns:
        df = df[df["Name"].astype(str).str.strip().str.lower() != "total"]
    return df


def _convert_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Convert vote-marker columns to boolean flags."""
    for col in df.columns:
        if col not in EXCLUDED_COLUMNS:
            series = df[col]
            df[col] = series.astype(str).str.strip().eq(VOTE_MARKER) & series.notna()
    return df


def _load_poll_csv(
    file: IO[Any] | str,
    label: str,
    column_label: str = "data",
) -> tuple[pd.DataFrame, list[str]]:
    """Parse a poll CSV into a cleaned DataFrame with boolean vote columns.

    Args:
        file: File path or file-like object.
        label: Label for error messages (e.g. "heavy games").
        column_label: Descriptor for data columns (e.g. "game", "time slot").

    Returns:
        Tuple of (parsed DataFrame, list of error strings).
    """
    try:
        df = pd.read_csv(file, quotechar='"')
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), [f"Failed to parse {label} CSV: {exc}"]

    if "Name" not in df.columns:
        return pd.DataFrame(), [f"{label} CSV missing 'Name' column"]

    df = _strip_totals(df)
    df["Name"] = df["Name"].astype(str).str.strip()
    df = _convert_votes(df)

    data_cols = [c for c in df.columns if c not in EXCLUDED_COLUMNS]
    if not data_cols:
        return df, [f"No {column_label} columns found in {label} CSV"]

    return df, []


def load_game_csv(
    file: IO[Any] | str, weight_class: str
) -> tuple[pd.DataFrame, list[str]]:
    """Parse a game poll CSV.

    Args:
        file: File path or file-like object.
        weight_class: Weight category label (e.g. "heavy", "medium").

    Returns:
        Tuple of (parsed DataFrame, list of error strings).
    """
    return _load_poll_csv(file, f"{weight_class} games", "game")


def load_timings_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a timings poll CSV.

    Returns:
        Tuple of (parsed DataFrame, list of error strings).
    """
    return _load_poll_csv(file, "timings", "time slot")


def load_place_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a place/location poll CSV.

    Returns:
        Tuple of (parsed DataFrame, list of error strings).
    """
    return _load_poll_csv(file, "place", "location")


def load_metadata_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse game metadata CSV.

    Expected columns: Name, Weight Class, Min Players, Max Players.

    Returns:
        Tuple of (parsed DataFrame, list of error strings).
    """
    try:
        df = pd.read_csv(file, quotechar='"')
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), [f"Failed to parse metadata CSV: {exc}"]

    required = {"Name", "Weight Class", "Min Players", "Max Players"}
    missing = required - set(df.columns)
    if missing:
        return pd.DataFrame(), [
            f"Metadata CSV missing columns: {', '.join(sorted(missing))}"
        ]

    df["Name"] = df["Name"].astype(str).str.strip()
    df["Weight Class"] = df["Weight Class"].astype(str).str.strip().str.lower()
    df["Min Players"] = (
        pd.to_numeric(df["Min Players"], errors="coerce").fillna(2).astype(int)
    )
    df["Max Players"] = (
        pd.to_numeric(df["Max Players"], errors="coerce").fillna(5).astype(int)
    )

    return df, []
