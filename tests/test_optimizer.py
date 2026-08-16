"""Tests for engine/optimizer.py — the MILP formulation itself.

Complements tests/test_selector.py (which exercises select_sessions, the
public entry point) with lower-level checks against select_optimal
directly: determinism, diagnostics, and hard-constraint proofs phrased in
terms of the solver's own output rather than the display layer.
"""

from __future__ import annotations

import copy

from models.entities import CandidateSession, Game
from models.config_model import SchedulerConfig
from engine.optimizer import select_optimal


def _candidate(game: str, slot: str, location: str, players: list[str]) -> CandidateSession:
    return CandidateSession(
        game=game,
        slot=slot,
        location=location,
        eligible_players=set(players),
        eligible_count=len(players),
        viable=True,
    )


def _games(
    *ids: str, min_players: int = 1, owner: str | None = None, weight_class: str = "medium"
) -> dict[str, Game]:
    return {
        gid: Game(id=gid, weight_class=weight_class, min_players=min_players, owner=owner)
        for gid in ids
    }


def _demand_from(candidates: list[CandidateSession]) -> dict[str, set[str]]:
    demand: dict[str, set[str]] = {}
    for c in candidates:
        demand.setdefault(c.game, set()).update(c.eligible_players)
    return demand


class TestEmptyInput:
    def test_no_candidates_returns_empty(self) -> None:
        selected, diagnostics = select_optimal([], SchedulerConfig(), {}, {})
        assert selected == []
        assert diagnostics == {}


class TestDeterminism:
    def test_identical_input_produces_identical_output_across_runs(self) -> None:
        """Same candidates, same config -> byte-identical schedule every time.

        Uses deep copies each run since select_optimal mutates
        assigned_players/assigned_count on the CandidateSession objects
        it's given.
        """
        base_candidates = [
            _candidate("Scythe", "Tuesday, 6 PM", "HSR Layout", ["A", "B", "C"]),
            _candidate("Scythe", "Wednesday, 6 PM", "Jayanagar", ["D", "E"]),
            _candidate("Catan", "Tuesday, 6 PM", "HSR Layout", ["B", "C", "F"]),
            _candidate("Catan", "Thursday, 6 PM", "HSR Layout", ["A", "G"]),
            _candidate("Wingspan", "Tuesday, 6 PM", "Jayanagar", ["H", "I"]),
        ]
        games = _games("Scythe", "Catan", "Wingspan")
        config = SchedulerConfig()

        results = []
        for _ in range(3):
            candidates = copy.deepcopy(base_candidates)
            demand = _demand_from(candidates)
            selected, diagnostics = select_optimal(candidates, config, games, demand)
            key = sorted(
                (c.game, c.slot, c.location, tuple(sorted(c.assigned_players)))
                for c in selected
            )
            results.append((key, diagnostics))

        assert all(r == results[0] for r in results)


class TestTableCapacityHardConstraint:
    def test_never_exceeds_capacity(self) -> None:
        candidates = [
            _candidate(f"G{i}", "S1", "L1", [f"P{i}"]) for i in range(5)
        ]
        games = _games(*[f"G{i}" for i in range(5)])
        demand = _demand_from(candidates)
        config = SchedulerConfig(max_tables_per_slot=3)
        selected, _ = select_optimal(candidates, config, games, demand)
        assert len(selected) <= 3


class TestRepeatLimitHardConstraint:
    def test_never_exceeds_max_repeats(self) -> None:
        candidates = [
            _candidate("G1", f"S{i}", "L1", [f"P{i}"]) for i in range(5)
        ]
        games = _games("G1")
        demand = _demand_from(candidates)
        config = SchedulerConfig(max_repeats_per_week=2, max_tables_per_slot=5)
        selected, _ = select_optimal(candidates, config, games, demand)
        assert len(selected) <= 2


class TestSingleCopyPerSlotHardConstraint:
    def test_same_game_never_runs_twice_in_the_same_slot_different_locations(self) -> None:
        """Only one physical copy exists — it can't be at two cafés at once,
        even though the table-capacity and repeat-limit constraints alone
        would otherwise permit it."""
        candidates = [
            _candidate("G1", "S1", "HSR Layout", ["A"]),
            _candidate("G1", "S1", "Jayanagar", ["B"]),
        ]
        games = _games("G1")
        demand = _demand_from(candidates)
        selected, _ = select_optimal(candidates, SchedulerConfig(), games, demand)
        assert len(selected) <= 1


class TestPlayerSlotExclusivityHardConstraint:
    def test_no_player_assigned_to_two_sessions_at_the_same_slot(self) -> None:
        candidates = [
            _candidate("G1", "S1", "HSR Layout", ["A", "B"]),
            _candidate("G2", "S1", "Jayanagar", ["A", "C"]),
        ]
        games = _games("G1", "G2")
        demand = _demand_from(candidates)
        selected, _ = select_optimal(candidates, SchedulerConfig(), games, demand)
        assigned_a_count = sum(1 for c in selected if "A" in c.assigned_players)
        assert assigned_a_count <= 1


class TestSingleVisitPerGameHardConstraint:
    def test_same_player_not_assigned_to_the_same_game_twice_in_the_week(self) -> None:
        """A player who voted for (and could attend) the same game at two
        different slots on different days is realistically not going to
        show up twice for the identical game — only one assignment across
        the whole week is allowed, even if both sessions run."""
        candidates = [
            _candidate("Scythe", "Tuesday, 6 PM", "HSR", ["A", "B"]),
            _candidate("Scythe", "Thursday, 6 PM", "HSR", ["A", "C"]),
        ]
        games = _games("Scythe")
        demand = _demand_from(candidates)
        config = SchedulerConfig(max_repeats_per_week=2, default_min_players=1)
        # Both games get min_players=1 via _games(); force it explicitly.
        games["Scythe"].min_players = 1
        selected, _ = select_optimal(candidates, config, games, demand)
        assigned_a_count = sum(1 for c in selected if "A" in c.assigned_players)
        assert assigned_a_count <= 1

    def test_different_games_for_the_same_player_are_unrestricted(self) -> None:
        """The constraint is per (player, game) — a repeat visit to attend
        a *different* game on a different day is a legitimate, unrestricted
        repeat customer visit."""
        candidates = [
            _candidate("Scythe", "Tuesday, 6 PM", "HSR", ["A"]),
            _candidate("Catan", "Thursday, 6 PM", "HSR", ["A"]),
        ]
        games = _games("Scythe", "Catan")
        demand = _demand_from(candidates)
        selected, _ = select_optimal(candidates, SchedulerConfig(), games, demand)
        assert len(selected) == 2
        assert all("A" in c.assigned_players for c in selected)


class TestDiagnostics:
    def test_diagnostics_report_every_stage(self) -> None:
        candidates = [
            _candidate("G1", "S1", "L1", ["A", "B"]),
            _candidate("G2", "S2", "L1", ["C"]),
        ]
        games = _games("G1", "G2")
        demand = _demand_from(candidates)
        _, diagnostics = select_optimal(candidates, SchedulerConfig(), games, demand)
        for key in (
            "players_covered",
            "revenue_weighted_attendance",
            "demand_weighted_score",
            "distinct_games",
            "session_count",
            "total_assigned_attendance",
        ):
            assert key in diagnostics
        assert diagnostics["players_covered"] == 3.0


class TestRevenueWeighting:
    def test_higher_revenue_weight_class_preferred_when_coverage_tied(self) -> None:
        """Two games reach the exact same players at the same slot/location
        (only one can run due to the single-copy... no, different games can
        coexist) — when coverage is tied, the heavier revenue weight wins
        the tie via the revenue stage."""
        c_heavy = _candidate("Heavy1", "S1", "L1", ["A", "B"])
        c_medium = _candidate("Medium1", "S1", "L1", ["A", "B"])
        games = {
            "Heavy1": Game(id="Heavy1", weight_class="heavy", min_players=1),
            "Medium1": Game(id="Medium1", weight_class="medium", min_players=1),
        }
        demand = _demand_from([c_heavy, c_medium])
        config = SchedulerConfig(
            max_tables_per_slot=1, revenue_weight_heavy=2.0, revenue_weight_medium=1.0
        )
        selected, _ = select_optimal([c_heavy, c_medium], config, games, demand)
        assert len(selected) == 1
        assert selected[0].game == "Heavy1"
