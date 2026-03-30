"""Tests for engine/explainer.py — reasoning traces."""

from __future__ import annotations

import pytest

from models.entities import CandidateSession, Game, SessionReasoning
from engine.explainer import explain_candidate, add_conflict_notes


@pytest.fixture
def context():
    candidate = CandidateSession(
        game="Kanban EV",
        slot="Tuesday, 6 PM",
        location="HSR Layout",
        eligible_players={"Alice", "Kiran", "Bob"},
        eligible_count=3,
        viability_score=0.75,
        score_breakdown={"demand": 0.9, "coverage": 0.5},
        viable=True,
    )
    demand_matrix = {
        "Kanban EV": {"Alice", "Kiran", "Bob", "Carol"},
        "Scythe": {"Alice", "Carol"},
    }
    games = {
        "Kanban EV": Game(id="Kanban EV", weight_class="heavy", owner="Kiran"),
        "Scythe": Game(id="Scythe", weight_class="medium"),
    }
    covered: set[str] = set()
    return candidate, demand_matrix, covered, games


class TestExplainCandidate:
    def test_reasoning_generated(self, context):
        candidate, demand, covered, games = context
        reasoning = explain_candidate(candidate, demand, covered, games, rank=1)
        assert isinstance(reasoning, SessionReasoning)
        assert "Kanban EV" in reasoning.demand_reason
        assert "3" in reasoning.overlap_reason
        assert "Ranked #1" in reasoning.selection_reason

    def test_owner_mentioned(self, context):
        candidate, demand, covered, games = context
        reasoning = explain_candidate(candidate, demand, covered, games)
        assert "Kiran" in reasoning.selection_reason

    def test_highest_demand_label(self, context):
        candidate, demand, covered, games = context
        reasoning = explain_candidate(candidate, demand, covered, games)
        assert "highest demand" in reasoning.demand_reason


class TestAddConflictNotes:
    def test_conflict_notes_added(self):
        s1 = CandidateSession(
            game="G1",
            slot="S1",
            location="L1",
            eligible_players={"Alice", "Bob"},
            eligible_count=2,
            viable=True,
            reasoning=SessionReasoning(
                demand_reason="", overlap_reason="", selection_reason=""
            ),
        )
        s2 = CandidateSession(
            game="G2",
            slot="S2",
            location="L1",
            eligible_players={"Alice", "Carol"},
            eligible_count=2,
            viable=True,
            reasoning=SessionReasoning(
                demand_reason="", overlap_reason="", selection_reason=""
            ),
        )
        add_conflict_notes([s1, s2])
        assert s1.reasoning.conflict_note is not None
        assert "Shares 1 player" in s1.reasoning.conflict_note

    def test_no_conflict_when_disjoint(self):
        s1 = CandidateSession(
            game="G1",
            slot="S1",
            location="L1",
            eligible_players={"Alice"},
            eligible_count=1,
            viable=True,
            reasoning=SessionReasoning(
                demand_reason="", overlap_reason="", selection_reason=""
            ),
        )
        s2 = CandidateSession(
            game="G2",
            slot="S2",
            location="L1",
            eligible_players={"Bob"},
            eligible_count=1,
            viable=True,
            reasoning=SessionReasoning(
                demand_reason="", overlap_reason="", selection_reason=""
            ),
        )
        add_conflict_notes([s1, s2])
        assert s1.reasoning.conflict_note is None
