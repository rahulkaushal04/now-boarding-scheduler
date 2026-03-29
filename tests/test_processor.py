"""Tests for data.processor — entity building and derived indices."""

from __future__ import annotations

import io

import pandas as pd
import pytest

from data.loader import (
    load_game_csv,
    load_metadata_csv,
    load_place_csv,
    load_timings_csv,
)
from data.processor import (
    build_conflict_matrix,
    build_demand_matrix,
    build_games,
    build_locations,
    build_overlap_map,
    build_players,
    build_slots,
)


def _csv(text: str) -> io.StringIO:
    """Return an in-memory CSV file."""
    return io.StringIO(text)


@pytest.fixture
def sample_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Provide sample CSV-derived DataFrames."""
    heavy_df, _ = load_game_csv(
        _csv(
            '"Name","Kanban EV (courtesy Kiran)","Scythe"\n'
            '"Alice","✓",""\n'
            '"Kiran","✓","✓"\n'
            '"Bob","","✓"\n'
        ),
        "heavy",
    )

    medium_df = pd.DataFrame(columns=["Name"])

    timings_df, _ = load_timings_csv(
        _csv(
            '"Name","Tuesday, 6 PM","Friday, 6 PM"\n'
            '"Alice","✓",""\n'
            '"Kiran","✓","✓"\n'
            '"Bob","","✓"\n'
        )
    )

    place_df, _ = load_place_csv(
        _csv(
            '"Name","HSR Layout","Jayanagar"\n'
            '"Alice","✓",""\n'
            '"Kiran","✓",""\n'
            '"Bob","✓",""\n'
        )
    )

    metadata_df, _ = load_metadata_csv(
        _csv(
            '"Name","Weight Class","Min Players","Max Players"\n'
            '"Kanban EV","heavy",2,4\n'
            '"Scythe","heavy",2,5\n'
        )
    )

    return heavy_df, medium_df, timings_df, place_df, metadata_df


class TestBuildPlayers:
    def test_player_prefs(self, sample_data) -> None:
        heavy_df, medium_df, timings_df, place_df, _ = sample_data

        players = build_players(heavy_df, medium_df, timings_df, place_df)

        assert "Alice" in players
        assert "Kanban EV" in players["Alice"].heavy_prefs
        assert "Tuesday, 6 PM" in players["Alice"].time_availability
        assert "HSR Layout" in players["Alice"].location_prefs


class TestBuildGames:
    def test_courtesy_owner_detected(self, sample_data) -> None:
        heavy_df, medium_df, _, place_df, metadata_df = sample_data

        empty_timings = pd.DataFrame(columns=["Name"])
        players = build_players(heavy_df, medium_df, empty_timings, place_df)

        games = build_games(heavy_df, medium_df, metadata_df, players)

        assert "Kanban EV" in games
        assert games["Kanban EV"].owner == "Kiran"

    def test_metadata_applied(self, sample_data) -> None:
        heavy_df, medium_df, _, place_df, metadata_df = sample_data

        empty_timings = pd.DataFrame(columns=["Name"])
        players = build_players(heavy_df, medium_df, empty_timings, place_df)

        games = build_games(heavy_df, medium_df, metadata_df, players)

        assert games["Kanban EV"].min_players == 2
        assert games["Kanban EV"].max_players == 4


class TestOverlapMap:
    def test_overlap_correctness(self, sample_data) -> None:
        heavy_df, medium_df, timings_df, place_df, metadata_df = sample_data

        players = build_players(heavy_df, medium_df, timings_df, place_df)
        games = build_games(heavy_df, medium_df, metadata_df, players)
        slots = build_slots(timings_df)
        locations = build_locations(place_df)

        overlap = build_overlap_map(players, games, slots, locations)

        key = ("Kanban EV", "Tuesday, 6 PM", "HSR Layout")

        assert "Alice" in overlap[key]
        assert "Kiran" in overlap[key]
        assert "Bob" not in overlap[key]


class TestConflictMatrix:
    def test_symmetry(self, sample_data) -> None:
        heavy_df, medium_df, timings_df, place_df, _ = sample_data

        players = build_players(heavy_df, medium_df, timings_df, place_df)
        demand = build_demand_matrix(players)
        conflicts = build_conflict_matrix(demand)

        for (g1, g2), value in conflicts.items():
            assert conflicts.get((g2, g1), 0) == value

    def test_shared_players(self, sample_data) -> None:
        heavy_df, medium_df, timings_df, place_df, _ = sample_data

        players = build_players(heavy_df, medium_df, timings_df, place_df)
        demand = build_demand_matrix(players)
        conflicts = build_conflict_matrix(demand)

        assert conflicts.get(("Kanban EV", "Scythe"), 0) >= 1
