"""Explainability layer — human-readable reasoning traces.

Zero Streamlit imports.  Pure Python.
"""
from __future__ import annotations

from models.entities import CandidateSession, Game, SessionReasoning


def explain_candidate(
    candidate: CandidateSession,
    demand_matrix: dict[str, set[str]],
    all_players: set[str],
    covered_players: set[str],
    games: dict[str, Game],
    rank: int | None = None,
) -> SessionReasoning:
    """Generate a human-readable reasoning trace for *candidate*."""
    total_interested = len(demand_matrix.get(candidate.game, set()))

    # --- Demand reason ---
    demand_reason = (
        f"{candidate.game} has {total_interested} interested "
        f"player{'s' if total_interested != 1 else ''}"
    )
    max_demand = max((len(s) for s in demand_matrix.values()), default=0)
    if total_interested == max_demand and total_interested > 0:
        demand_reason += " \u2014 highest demand this week"
    elif max_demand > 0 and total_interested >= max_demand * 0.7:
        demand_reason += " \u2014 high demand"

    # --- Overlap reason ---
    overlap_reason = (
        f"{candidate.eligible_count} of those {total_interested} are free at "
        f"{candidate.slot} and prefer {candidate.location}"
    )

    # --- Selection reason ---
    new_players = candidate.eligible_players - covered_players
    parts: list[str] = []
    if rank is not None:
        parts.append(f"Ranked #{rank}")
    parts.append(
        f"Covers {len(new_players)} new "
        f"player{'s' if len(new_players) != 1 else ''}"
    )
    game = games.get(candidate.game)
    if game and game.owner and game.owner in candidate.eligible_players:
        parts.append(f"Owner {game.owner} is available")
    selection_reason = ". ".join(parts) + "."

    return SessionReasoning(
        demand_reason=demand_reason,
        overlap_reason=overlap_reason,
        selection_reason=selection_reason,
        conflict_note=None,
        score_breakdown=candidate.score_breakdown.copy(),
    )


def add_conflict_notes(
    selected: list[CandidateSession],
    conflict_matrix: dict[tuple[str, str], int],
) -> None:
    """Attach conflict notes to each selected session describing shared
    players with other selected sessions.  Mutates ``reasoning`` in place.
    """
    for i, sess in enumerate(selected):
        conflicts: list[str] = []
        for j, other in enumerate(selected):
            if i == j:
                continue
            shared = len(sess.eligible_players & other.eligible_players)
            if shared > 0:
                conflicts.append(
                    f"Shares {shared} player{'s' if shared != 1 else ''} "
                    f"with {other.game}"
                )
        if conflicts and sess.reasoning:
            sess.reasoning.conflict_note = ". ".join(conflicts) + "."
