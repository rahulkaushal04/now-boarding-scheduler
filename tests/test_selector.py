"""Tests for engine/selector.py — greedy session selection."""
from __future__ import annotations

import pytest

from models.entities import CandidateSession
from models.config_model import SchedulerConfig
from engine.selector import select_sessions


def _candidate(game, slot, location, players, score):
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
    def test_respects_max_tables(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S1", "L1", ["C", "D"], 0.8)
        config = SchedulerConfig(target_sessions=2, max_tables_per_slot=1)
        selected = select_sessions([c1, c2], config, {}, {"A", "B", "C", "D"})
        assert len(selected) == 1  # second rejected (same slot+location)

    def test_different_locations_ok(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S1", "L2", ["C", "D"], 0.8)
        config = SchedulerConfig(target_sessions=2, max_tables_per_slot=1)
        selected = select_sessions([c1, c2], config, {}, {"A", "B", "C", "D"})
        assert len(selected) == 2


class TestStopsAtTarget:
    def test_stops(self):
        candidates = [
            _candidate(f"G{i}", f"S{i}", "L1", [f"P{i}"], 0.9 - i * 0.1)
            for i in range(5)
        ]
        config = SchedulerConfig(target_sessions=3, max_tables_per_slot=5)
        selected = select_sessions(candidates, config, {}, {f"P{i}" for i in range(5)})
        assert len(selected) == 3


class TestCoverageBonus:
    def test_prefers_new_players(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"], 0.9)
        c2 = _candidate("G2", "S2", "L1", ["A", "B"], 0.85)  # same players
        c3 = _candidate("G3", "S3", "L1", ["C", "D"], 0.80)  # new players
        config = SchedulerConfig(target_sessions=2, max_tables_per_slot=1)
        all_p = {"A", "B", "C", "D"}
        selected = select_sessions([c1, c2, c3], config, {}, all_p)
        games = {s.game for s in selected}
        assert "G1" in games


class TestConflictPenalty:
    def test_conflict_penalty_same_slot(self):
        # Both at same slot with overlapping players
        c1 = _candidate("G1", "S1", "L1", ["A", "B", "C"], 0.9)
        c2 = _candidate("G2", "S1", "L2", ["A", "B", "D"], 0.85)
        c3 = _candidate("G3", "S2", "L1", ["E", "F"], 0.80)
        config = SchedulerConfig(target_sessions=2, max_tables_per_slot=1)
        all_p = {"A", "B", "C", "D", "E", "F"}
        selected = select_sessions([c1, c2, c3], config, {}, all_p)
        # c1 should be selected, then c3 (c2 conflicts heavily with c1)
        assert len(selected) == 2
