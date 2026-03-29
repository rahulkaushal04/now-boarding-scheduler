"""Layer 2 — Greedy session selection.

Zero Streamlit imports.  Pure Python.
"""
from __future__ import annotations

from models.entities import CandidateSession
from models.config_model import SchedulerConfig


def select_sessions(
    candidates: list[CandidateSession],
    config: SchedulerConfig,
    conflict_matrix: dict[tuple[str, str], int],
    all_players: set[str],
) -> list[CandidateSession]:
    """Greedy-pick the top *target_sessions* non-conflicting candidates.

    Iterates viable candidates in Layer-1 score order and enforces:
    * table capacity per (location, slot)
    * max repeats per game per week
    * coverage bonus for sessions that serve uncovered players
    * conflict penalty for sessions sharing players at the same slot
    * diminishing-returns diversity multiplier for repeated games

    Returns selected sessions sorted by time slot.
    """
    viable = [c for c in candidates if c.viable]

    selected: list[CandidateSession] = []
    # (location, slot) → number of tables already booked
    occupied: dict[tuple[str, str], int] = {}
    covered_players: set[str] = set()
    game_counts: dict[str, int] = {}

    for candidate in viable:
        loc_slot = (candidate.location, candidate.slot)

        # Hard: table capacity
        if occupied.get(loc_slot, 0) >= config.max_tables_per_slot:
            continue

        # Hard: repeat limit
        if game_counts.get(candidate.game, 0) >= config.max_repeats_per_week:
            continue

        # Soft: conflict penalty — shared players with an already-selected
        # session **at the same slot**
        conflict_penalty = 0.0
        for sel in selected:
            if sel.slot == candidate.slot:
                shared = len(candidate.eligible_players & sel.eligible_players)
                union = len(candidate.eligible_players | sel.eligible_players)
                if union > 0:
                    conflict_penalty += shared / union

        # Soft: coverage bonus
        uncovered = all_players - covered_players
        new_players = candidate.eligible_players - covered_players
        coverage_bonus = len(new_players) / len(uncovered) if uncovered else 0.0

        # Soft: diminishing returns for repeated games
        game_count = game_counts.get(candidate.game, 0)
        diversity_mult = 1.0 / (2 ** game_count)

        adjusted = (
            candidate.viability_score * diversity_mult
            + 0.3 * coverage_bonus
            - 0.2 * conflict_penalty
        )

        # Accept if adjusted score is positive (or schedule is still empty)
        if adjusted > 0 or not selected:
            selected.append(candidate)
            occupied[loc_slot] = occupied.get(loc_slot, 0) + 1
            covered_players.update(candidate.eligible_players)
            game_counts[candidate.game] = game_count + 1

        if len(selected) >= config.target_sessions:
            break

    # Present in time-slot order
    selected.sort(key=lambda c: c.slot)
    return selected
