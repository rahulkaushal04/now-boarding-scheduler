"""Layer 1 — Score every (game, slot, location) candidate.

Zero Streamlit imports.  Pure Python.
"""
from __future__ import annotations

from models.entities import CandidateSession, Game, Slot, Location
from config import (
    W_DEMAND,
    W_DIVERSITY,
    W_COVERAGE,
    W_POPULARITY,
    W_AVAILABILITY,
    W_LOCATION,
)


def _norm(value: float, maximum: float) -> float:
    """Normalise *value* into [0, 1].  Returns 0 when *maximum* ≤ 0."""
    if maximum <= 0:
        return 0.0
    return min(value / maximum, 1.0)


def score_all_candidates(
    overlap_map: dict[tuple[str, str, str], set[str]],
    games: dict[str, Game],
    demand_matrix: dict[str, set[str]],
    slots: dict[str, Slot],
    locations: dict[str, Location],
    all_players: set[str],
) -> list[CandidateSession]:
    """Score every (game, slot, location) triple.

    Applies game-rule hard filters first, then computes the 6-component
    weighted viability score.  Returns **all** candidates sorted with
    viable ones first (descending score) then non-viable ones.
    """
    candidates: list[CandidateSession] = []

    # Pre-compute normalisation ceilings
    max_overlap = max((len(s) for s in overlap_map.values()), default=0)
    max_demand = max((len(s) for s in demand_matrix.values()), default=0)
    total_player_count = len(all_players)

    # Slot density: unique players available at each slot (across all games/locations)
    slot_player_sets: dict[str, set[str]] = {sid: set() for sid in slots}
    for (_, sid, _), pset in overlap_map.items():
        if sid in slot_player_sets:
            slot_player_sets[sid].update(pset)
    slot_density = {sid: len(pset) for sid, pset in slot_player_sets.items()}
    max_slot_density = max(slot_density.values(), default=0)

    for game_id, game in games.items():
        for slot_id, slot in slots.items():
            for loc_id in locations:
                eligible = overlap_map.get((game_id, slot_id, loc_id), set())

                candidate = CandidateSession(
                    game=game_id,
                    slot=slot_id,
                    location=loc_id,
                    eligible_players=eligible.copy(),
                    eligible_count=len(eligible),
                )

                # --- Hard filter: allowed days ---
                if game.allowed_days is not None and slot.day not in game.allowed_days:
                    candidate.viable = False
                    candidate.rejection_reason = (
                        f"{game_id} restricted to "
                        f"{', '.join(sorted(game.allowed_days))} "
                        f"\u2014 {slot.day} rejected"
                    )
                    candidates.append(candidate)
                    continue

                # --- Hard filter: location lock ---
                if game.location_lock is not None and loc_id != game.location_lock:
                    candidate.viable = False
                    candidate.rejection_reason = (
                        f"{game_id} locked to {game.location_lock} "
                        f"\u2014 {loc_id} rejected"
                    )
                    candidates.append(candidate)
                    continue

                # --- Hard filter: owner availability ---
                if game.owner is not None and game.owner not in eligible:
                    candidate.viable = False
                    candidate.rejection_reason = (
                        f"Owner {game.owner} is not available at "
                        f"{slot_id} / {loc_id}"
                    )
                    candidates.append(candidate)
                    continue

                # --- Hard filter: minimum players ---
                if len(eligible) < game.min_players:
                    candidate.viable = False
                    candidate.rejection_reason = (
                        f"Only {len(eligible)} eligible "
                        f"player{'s' if len(eligible) != 1 else ''} "
                        f"\u2014 below minimum of {game.min_players}"
                    )
                    candidates.append(candidate)
                    continue

                # --- Scoring components ---
                demand_score = _norm(len(eligible), max_overlap)
                popularity_score = _norm(
                    len(demand_matrix.get(game_id, set())), max_demand
                )
                availability_score = _norm(
                    slot_density.get(slot_id, 0), max_slot_density
                )

                # Location alignment: fraction of game demand at this location
                total_demand = len(demand_matrix.get(game_id, set()))
                location_score = (
                    len(eligible) / total_demand if total_demand > 0 else 0.0
                )

                # Diversity: niche games (lower demand ratio) score higher
                diversity_score = (
                    1.0 - (total_demand / total_player_count)
                    if total_player_count > 0
                    else 0.0
                )

                # Coverage potential: what fraction of all players this serves
                coverage_score = (
                    len(eligible) / total_player_count
                    if total_player_count > 0
                    else 0.0
                )

                breakdown = {
                    "demand": round(demand_score, 4),
                    "popularity": round(popularity_score, 4),
                    "availability": round(availability_score, 4),
                    "location": round(location_score, 4),
                    "diversity": round(diversity_score, 4),
                    "coverage": round(coverage_score, 4),
                }

                viability = (
                    W_DEMAND * demand_score
                    + W_POPULARITY * popularity_score
                    + W_AVAILABILITY * availability_score
                    + W_LOCATION * location_score
                    + W_DIVERSITY * diversity_score
                    + W_COVERAGE * coverage_score
                )

                candidate.viability_score = round(viability, 4)
                candidate.score_breakdown = breakdown
                candidate.viable = True
                candidates.append(candidate)

    # Viable first (descending score), then non-viable
    candidates.sort(key=lambda c: (-int(c.viable), -c.viability_score))
    return candidates
