"""CSV loading and parsing for game polls, timings, places, and metadata."""

from typing import IO, Any

import pandas as pd

from config import EXCLUDED_COLUMNS, VOTE_MARKER


def _strip_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Remove 'Total' summary rows and columns from a poll DataFrame.

    Strips any column whose header is exactly 'Total' and the row where
    the Name column equals 'total' (case-insensitive), as these are
    spreadsheet summaries rather than participant data.

    Args:
        df (pd.DataFrame): Raw poll DataFrame that may contain summary rows
            and columns.

    Returns:
        pd.DataFrame: DataFrame with Total rows and columns removed.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Name": ["Alice", "Total"], "G": [True, 1]})
        >>> result = _strip_totals(df)
        >>> len(result)
        1
    """
    df = df.drop(
        columns=[c for c in df.columns if str(c).strip() == "Total"],
        errors="ignore",
    )
    if "Name" in df.columns:
        df = df[df["Name"].astype(str).str.strip().str.lower() != "total"]
    return df


def _convert_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Convert vote-marker columns to boolean flags.

    Cells matching VOTE_MARKER (✓) become ``True``; all others become
    ``False``.  The Name and Total columns are left unchanged.

    Args:
        df (pd.DataFrame): Poll DataFrame with raw vote-marker strings.

    Returns:
        pd.DataFrame: Same DataFrame with vote columns replaced by booleans.

    Example:
        >>> import pandas as pd
        >>> from config import VOTE_MARKER
        >>> df = pd.DataFrame({"Name": ["Alice"], "GameA": [VOTE_MARKER]})
        >>> bool(_convert_votes(df).iloc[0]["GameA"])
        True
    """
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
        file (IO[Any] | str): File path or file-like object.
        label (str): Label for error messages (e.g. ``"heavy games"``).
        column_label (str): Descriptor for data columns used in warnings
            (e.g. ``"game"``, ``"time slot"``).

    Returns:
        tuple[pd.DataFrame, list[str]]: Parsed DataFrame and a list of error
            strings (empty on success).
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
        file (IO[Any] | str): File path or file-like object.
        weight_class (str): Weight category label (e.g. ``"heavy"``,
            ``"medium"``).

    Returns:
        tuple[pd.DataFrame, list[str]]: Parsed DataFrame and error strings.

    Example:
        >>> import io
        >>> csv = io.StringIO('"Name","GameA"\\n"Alice","✓"\\n')
        >>> df, errors = load_game_csv(csv, "heavy")
        >>> errors
        []
    """
    return _load_poll_csv(file, f"{weight_class} games", "game")


def load_timings_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a timings poll CSV.

    Args:
        file (IO[Any] | str): File path or file-like object.

    Returns:
        tuple[pd.DataFrame, list[str]]: Parsed DataFrame and error strings.
    """
    return _load_poll_csv(file, "timings", "time slot")


def load_place_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a place/location poll CSV.

    Args:
        file (IO[Any] | str): File path or file-like object.

    Returns:
        tuple[pd.DataFrame, list[str]]: Parsed DataFrame and error strings.
    """
    return _load_poll_csv(file, "place", "location")


def load_metadata_csv(file: IO[Any] | str) -> tuple[pd.DataFrame, list[str]]:
    """Parse game metadata CSV.

    Expected columns: Name, Weight Class, Min Players, Max Players.

    Args:
        file (IO[Any] | str): File path or file-like object.

    Returns:
        tuple[pd.DataFrame, list[str]]: Parsed DataFrame and error strings.

    Raises:
        None: Errors are returned in the list rather than raised.
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
