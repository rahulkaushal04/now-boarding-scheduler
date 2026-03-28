from __future__ import annotations

from typing import IO, Any

import pandas as pd

# Constants
VOTE_MARKER = "\u2713"  # ✓ (Unicode U+2713)
EXCLUDED_COLUMNS = {"Name", "Total"}


def _strip_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows/columns labeled 'Total'."""
    df = df.drop(
        columns=[c for c in df.columns if str(c).strip() == "Total"],
        errors="ignore",
    )

    if "Name" in df.columns:
        name_series = df["Name"].astype(str)
        df = df[name_series.str.strip().str.lower() != "total"]

    return df


def _convert_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Convert vote marker columns to boolean flags."""
    data_cols = [c for c in df.columns if c not in EXCLUDED_COLUMNS]

    for col in data_cols:
        series = df[col]
        df[col] = series.astype(str).str.strip().eq(VOTE_MARKER) & series.notna()

    return df


def load_game_csv(
    file: IO[Any] | str, weight_class: str
) -> tuple[pd.DataFrame, list[str]]:
    """Parse a game poll CSV.

    Columns other than 'Name'/'Total' are treated as game names and
    converted to boolean vote flags.

    Returns:
        tuple[pd.DataFrame, list[str]]: (dataframe, errors)
    """
    errors: list[str] = []

    try:
        df = pd.read_csv(file, quotechar='"')
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), [f"Failed to parse {weight_class} games CSV: {exc}"]

    if "Name" not in df.columns:
        return pd.DataFrame(), [f"{weight_class} games CSV missing 'Name' column"]

    df = _strip_totals(df)
    df["Name"] = df["Name"].astype(str).str.strip()
    df = _convert_votes(df)

    game_cols = [c for c in df.columns if c not in EXCLUDED_COLUMNS]
    if not game_cols:
        errors.append(f"No game columns found in {weight_class} games CSV")

    return df, errors


def load_timings_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a timings poll CSV.

    Returns:
        tuple[pd.DataFrame, list[str]]: (dataframe, errors)
    """
    errors: list[str] = []

    try:
        df = pd.read_csv(file, quotechar='"')
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), [f"Failed to parse timings CSV: {exc}"]

    if "Name" not in df.columns:
        return pd.DataFrame(), ["Timings CSV missing 'Name' column"]

    df = _strip_totals(df)
    df["Name"] = df["Name"].astype(str).str.strip()
    df = _convert_votes(df)

    slot_cols = [c for c in df.columns if c not in EXCLUDED_COLUMNS]
    if not slot_cols:
        errors.append("No time slot columns found in timings CSV")

    return df, errors


def load_place_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a place/location poll CSV.

    Returns:
        tuple[pd.DataFrame, list[str]]: (dataframe, errors)
    """
    errors: list[str] = []

    try:
        df = pd.read_csv(file, quotechar='"')
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), [f"Failed to parse place CSV: {exc}"]

    if "Name" not in df.columns:
        return pd.DataFrame(), ["Place CSV missing 'Name' column"]

    df = _strip_totals(df)
    df["Name"] = df["Name"].astype(str).str.strip()
    df = _convert_votes(df)

    loc_cols = [c for c in df.columns if c not in EXCLUDED_COLUMNS]
    if not loc_cols:
        errors.append("No location columns found in place CSV")

    return df, errors


def load_metadata_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse game metadata CSV.

    Expected columns:
        Name, Weight Class, Min Players, Max Players

    Returns:
        tuple[pd.DataFrame, list[str]]: (dataframe, errors)
    """
    errors: list[str] = []

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

    return df, errors
