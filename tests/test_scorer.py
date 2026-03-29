"""Tests for engine/scorer.py — scoring components and viability gates."""
from __future__ import annotations

import pytest

from models.entities import Game, Slot, Location
from engine.scorer import score_all_candidates


@pytest.fixture
def simple_scenario():
    """Minimal scenario: 2 games, 1 slot, 1 location, 3 players."""
    games = {
        "GameA": Game(id="GameA", weight_class="heavy", min_players=2, max_players=4),
        "GameB": Game(id="GameB", weight_class="medium", min_players=2, max_players=4),
    }
    slots = {"Tue 6 PM": Slot(id="Tue 6 PM", day="Tuesday", time="6 PM")}
    locations = {"HSR": Location(id="HSR")}
    overlap_map = {
        ("GameA", "Tue 6 PM", "HSR"): {"Alice", "Bob", "Carol"},
        ("GameB", "Tue 6 PM", "HSR"): {"Alice", "Carol"},
    }
    demand_matrix = {
        "GameA": {"Alice", "Bob", "Carol"},
        "GameB": {"Alice", "Carol"},
    }
    all_players = {"Alice", "Bob", "Carol"}
    return overlap_map, games, demand_matrix, slots, locations, all_players


class TestScorerComponents:
    def test_scores_in_range(self, simple_scenario):
        candidates = score_all_candidates(*simple_scenario)
        for c in candidates:
            if c.viable:
                assert 0.0 <= c.viability_score <= 1.0
                for v in c.score_breakdown.values():
                    assert 0.0 <= v <= 1.0

    def test_viable_flag(self, simple_scenario):
        candidates = score_all_candidates(*simple_scenario)
        viable = [c for c in candidates if c.viable]
        assert len(viable) >= 1


class TestViabilityGate:
    def test_below_min_players_rejected(self):
        games = {"G": Game(id="G", weight_class="heavy", min_players=5)}
        slots = {"S": Slot(id="S", day="Tue", time="6 PM")}
        locations = {"L": Location(id="L")}
        overlap = {("G", "S", "L"): {"Alice"}}
        demand = {"G": {"Alice"}}
        candidates = score_all_candidates(overlap, games, demand, slots, locations, {"Alice"})
        assert all(not c.viable for c in candidates)
        assert "below minimum" in candidates[0].rejection_reason


class TestGameRuleFilters:
    def test_owner_missing_rejected(self):
        games = {"G": Game(id="G", weight_class="heavy", min_players=1, owner="Kiran")}
        slots = {"S": Slot(id="S", day="Tue", time="6 PM")}
        locations = {"L": Location(id="L")}
        overlap = {("G", "S", "L"): {"Alice"}}  # Kiran not in eligible
        demand = {"G": {"Alice", "Kiran"}}
        candidates = score_all_candidates(overlap, games, demand, slots, locations, {"Alice", "Kiran"})
        assert all(not c.viable for c in candidates)
        assert "Owner Kiran" in candidates[0].rejection_reason

    def test_day_restriction_rejected(self):
        games = {"G": Game(id="G", weight_class="heavy", min_players=1, allowed_days={"Friday"})}
        slots = {"S": Slot(id="S", day="Tuesday", time="6 PM")}
        locations = {"L": Location(id="L")}
        overlap = {("G", "S", "L"): {"Alice"}}
        demand = {"G": {"Alice"}}
        candidates = score_all_candidates(overlap, games, demand, slots, locations, {"Alice"})
        assert all(not c.viable for c in candidates)
        assert "Tuesday rejected" in candidates[0].rejection_reason

    def test_location_lock_rejected(self):
        games = {"G": Game(id="G", weight_class="heavy", min_players=1, location_lock="HSR")}
        slots = {"S": Slot(id="S", day="Tue", time="6 PM")}
        locations = {"Jayanagar": Location(id="Jayanagar")}
        overlap = {("G", "S", "Jayanagar"): {"Alice"}}
        demand = {"G": {"Alice"}}
        candidates = score_all_candidates(overlap, games, demand, slots, locations, {"Alice"})
        assert all(not c.viable for c in candidates)
        assert "locked to HSR" in candidates[0].rejection_reason
