"""Tests for CSV parsing utilities in data.loader."""

from __future__ import annotations

import io

import pytest

from data.loader import (
    load_game_csv,
    load_metadata_csv,
    load_place_csv,
    load_timings_csv,
)


def _make_csv(text: str) -> io.StringIO:
    """Return an in-memory CSV file."""
    return io.StringIO(text)


# ---- Heavy/Medium game CSV ----


class TestLoadGameCsv:
    def test_basic_loading(self) -> None:
        csv = _make_csv(
            '"Name","GameA","GameB","Total"\n'
            '"Alice","✓","","1"\n'
            '"Bob","","✓","1"\n'
            '"Total","1","1","2"\n'
        )
        df, errors = load_game_csv(csv, "heavy")

        assert not errors
        assert len(df) == 2
        assert "Total" not in df.columns
        assert bool(df.iloc[0]["GameA"]) is True
        assert bool(df.iloc[0]["GameB"]) is False

    def test_total_filtered(self) -> None:
        csv = _make_csv(
            '"Name","GameA","Total"\n' '"Alice","✓","1"\n' '"Total","1","1"\n'
        )
        df, _ = load_game_csv(csv, "medium")

        assert "Total" not in df.columns
        assert len(df) == 1

    def test_vote_marker(self) -> None:
        csv = _make_csv('"Name","GameA"\n' '"Alice","✓"\n' '"Bob","x"\n' '"Carol",""\n')
        df, _ = load_game_csv(csv, "heavy")

        assert bool(df.iloc[0]["GameA"]) is True
        assert bool(df.iloc[1]["GameA"]) is False
        assert bool(df.iloc[2]["GameA"]) is False

    def test_missing_name_column(self) -> None:
        csv = _make_csv('"Player","GameA"\n"Alice","✓"\n')
        _, errors = load_game_csv(csv, "heavy")

        assert any("Name" in e for e in errors)

    def test_quoted_names(self) -> None:
        csv = _make_csv('"Name","GameA"\n' '"Vasudev ""Draconite""","✓"\n')
        df, errors = load_game_csv(csv, "heavy")

        assert not errors
        assert "Draconite" in df.iloc[0]["Name"]

    def test_empty_file(self) -> None:
        csv = _make_csv("")
        _, errors = load_game_csv(csv, "heavy")

        assert len(errors) > 0


# ---- Timings CSV ----


class TestLoadTimingsCsv:
    def test_basic(self) -> None:
        csv = _make_csv(
            '"Name","Tuesday, 6 PM","Friday, 6 PM","Total"\n'
            '"Alice","✓","","1"\n'
            '"Total","1","0","1"\n'
        )
        df, errors = load_timings_csv(csv)

        assert not errors
        assert len(df) == 1
        assert bool(df.iloc[0]["Tuesday, 6 PM"]) is True
        assert bool(df.iloc[0]["Friday, 6 PM"]) is False

    def test_missing_name(self) -> None:
        csv = _make_csv('"Player","Slot"\n')
        _, errors = load_timings_csv(csv)

        assert any("Name" in e for e in errors)


# ---- Place CSV ----


class TestLoadPlaceCsv:
    def test_basic(self) -> None:
        csv = _make_csv(
            '"Name","HSR Layout","Jayanagar","Total"\n'
            '"Alice","✓","","1"\n'
            '"Total","1","0","1"\n'
        )
        df, errors = load_place_csv(csv)

        assert not errors
        assert len(df) == 1
        assert bool(df.iloc[0]["HSR Layout"]) is True

    def test_missing_name(self) -> None:
        csv = _make_csv('"Player","Loc"\n')
        _, errors = load_place_csv(csv)

        assert any("Name" in e for e in errors)


# ---- Metadata CSV ----


class TestLoadMetadataCsv:
    def test_basic(self) -> None:
        csv = _make_csv(
            '"Name","Weight Class","Min Players","Max Players"\n'
            '"Scythe","medium",1,5\n'
        )
        df, errors = load_metadata_csv(csv)

        assert not errors
        assert df.iloc[0]["Min Players"] == 1
        assert df.iloc[0]["Max Players"] == 5
        assert df.iloc[0]["Weight Class"] == "medium"

    def test_missing_columns(self) -> None:
        csv = _make_csv('"Name","Min Players"\n"Scythe",2\n')
        _, errors = load_metadata_csv(csv)

        assert len(errors) > 0
