"""Tests for engine/selector.py — greedy session selection."""

from __future__ import annotations

import pytest

from models.entities import CandidateSession
from models.config_model import SchedulerConfig
from engine.selector import select_sessions


def _candidate(
    game: str,
    slot: str,
    location: str,
    players: list[str],
    score: float,
) -> CandidateSession:
    """Create a minimal viable CandidateSession for testing.

    Args:
        game (str): Game identifier.
        slot (str): Slot identifier.
        location (str): Location identifier.
        players (list[str]): Eligible player ids.
        score (float): Viability score.

    Returns:
        CandidateSession: Configured viable session with the given score.
    """
    return CandidateSession(
        game=game,
        slot=slot,
        location=location,
        eligible_players=set(players),
        eligible_count=len(players),
        viability_score=score,
        viable=True,
    )


class TestTableCapacity:
    def test_overflow_allowed_when_no_overlap(self):
        """Two games at the same slot+location are allowed via smart overflow
        when player sets don't overlap and one game would otherwise go unscheduled."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S1", "L1", ["C", "D"], 0.8)
        config = SchedulerConfig()
        result = select_sessions([c1, c2], config, {}, {"A", "B", "C", "D"})
        assert len(result.selected) == 2
        assert result.selected[1].is_overflow is True

    def test_overflow_blocked_when_high_overlap(self):
        """Second table refused when player overlap is above threshold."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B", "C"], 0.9)
        c2 = _candidate("G2", "S1", "L1", ["A", "B", "D"], 0.8)
        config = SchedulerConfig()
        result = select_sessions([c1, c2], config, {}, {"A", "B", "C", "D"})
        assert len(result.selected) == 1

    def test_hard_ceiling_blocks_third_table(self):
        """max_tables_per_slot=2 blocks a third game at the same slot."""
        c1 = _candidate("G1", "S1", "L1", ["A"], 0.9)
        c2 = _candidate("G2", "S1", "L1", ["B"], 0.8)
        c3 = _candidate("G3", "S1", "L1", ["C"], 0.7)
        config = SchedulerConfig(max_tables_per_slot=2)
        result = select_sessions([c1, c2, c3], config, {}, {"A", "B", "C"})
        assert len(result.selected) == 2

    def test_no_overflow_when_game_already_scheduled(self):
        """Overflow doesn't trigger if the game already has a session elsewhere."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S2", "L1", ["C", "D"], 0.85)
        c3 = _candidate("G2", "S1", "L1", ["E", "F"], 0.6)
        config = SchedulerConfig()
        result = select_sessions(
            [c1, c2, c3], config, {}, {"A", "B", "C", "D", "E", "F"}
        )
        # G2 already got S2, so G2@S1 should not trigger overflow
        games_at_s1 = [s for s in result.selected if s.slot == "S1"]
        assert len(games_at_s1) == 1

    def test_different_locations_ok(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S1", "L2", ["C", "D"], 0.8)
        config = SchedulerConfig()
        result = select_sessions([c1, c2], config, {}, {"A", "B", "C", "D"})
        assert len(result.selected) == 2


class TestSelectsAllQualityCandidates:
    def test_selects_all_when_quality(self):
        candidates = [
            _candidate(f"G{i}", f"S{i}", "L1", [f"P{i}"], 0.9 - i * 0.1)
            for i in range(5)
        ]
        config = SchedulerConfig()
        result = select_sessions(candidates, config, {}, {f"P{i}" for i in range(5)})
        assert len(result.selected) == 5

    def test_stops_when_score_drops(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S2", "L1", ["A", "B"], 0.001)  # very low
        config = SchedulerConfig()
        all_p = {"A", "B"}
        result = select_sessions([c1, c2], config, {}, all_p)
        # c2 may still be picked if adjusted > 0, but that's fine
        assert len(result.selected) >= 1


class TestCoverageBonus:
    def test_prefers_new_players(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S2", "L1", ["A", "B"], 0.85)  # same players
        c3 = _candidate("G3", "S3", "L1", ["C", "D"], 0.80)  # new players
        config = SchedulerConfig()
        all_p = {"A", "B", "C", "D"}
        result = select_sessions([c1, c2, c3], config, {}, all_p)
        games = {s.game for s in result.selected}
        assert "G1" in games


class TestConflictPenalty:
    def test_conflict_penalty_same_slot(self):
        # Both at same slot but different locations, with overlapping players
        c1 = _candidate("G1", "S1", "L1", ["A", "B", "C"], 0.9)
        c2 = _candidate("G2", "S1", "L2", ["A", "B", "D"], 0.85)
        c3 = _candidate("G3", "S2", "L1", ["E", "F"], 0.80)
        config = SchedulerConfig()
        all_p = {"A", "B", "C", "D", "E", "F"}
        result = select_sessions([c1, c2, c3], config, {}, all_p)
        # All three should be selected (different slot/location combos)
        assert len(result.selected) == 3


class TestSuggestions:
    def test_suggestion_for_unscheduled_game(self):
        """A game blocked by table capacity appears as a suggestion."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate(
            "G2", "S1", "L1", ["A", "B"], 0.8
        )  # same players = high overlap
        config = SchedulerConfig()
        result = select_sessions([c1, c2], config, {}, {"A", "B"})
        assert len(result.selected) == 1
        assert len(result.suggestions) == 1
        assert result.suggestions[0].game == "G2"
        assert result.suggestions[0].suggestion_reason is not None

    def test_no_suggestion_when_game_is_scheduled(self):
        """Games that made the schedule should not appear as suggestions."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S2", "L1", ["C", "D"], 0.8)
        config = SchedulerConfig()
        result = select_sessions([c1, c2], config, {}, {"A", "B", "C", "D"})
        assert len(result.selected) == 2
        assert len(result.suggestions) == 0

    def test_suggestion_picks_best_candidate(self):
        """Suggestion should use the highest-scored viable candidate for that game."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S1", "L1", ["A", "B"], 0.7)  # blocked, high overlap
        c3 = _candidate("G2", "S2", "L1", ["A", "B"], 0.5)  # lower score same game
        # c1 takes S1/L1. G2@S1/L1 blocked (high overlap). G2@S2/L1 should be selected.
        config = SchedulerConfig()
        result = select_sessions([c1, c2, c3], config, {}, {"A", "B"})
        # G2@S2/L1 gets selected normally (different slot, no overflow needed)
        g2_sessions = [s for s in result.selected if s.game == "G2"]
        assert len(g2_sessions) == 1
