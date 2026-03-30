"""Layer 2 — Greedy session selection with smart overflow and suggestions."""

from models.entities import CandidateSession, SelectionResult
from models.config_model import SchedulerConfig

# Jaccard overlap above this threshold blocks a second table at a slot.
_OVERFLOW_CONFLICT_THRESHOLD = 0.5


def _qualifies_for_overflow(
    candidate: CandidateSession,
    game_counts: dict[str, int],
    selected: list[CandidateSession],
) -> bool:
    """Check if a candidate qualifies for a second table at an occupied slot.

    A second table is only opened when:
    1. The game has zero sessions scheduled (would be entirely unscheduled).
    2. Player overlap with the existing session(s) at the same (slot, location)
       is below the conflict threshold — the two tables serve different groups.

    Args:
        candidate (CandidateSession): The candidate being evaluated.
        game_counts (dict[str, int]): Number of sessions already scheduled
            per game id.
        selected (list[CandidateSession]): Already-selected sessions.

    Returns:
        bool: ``True`` if the candidate may open a second table.
    """
    if game_counts.get(candidate.game, 0) > 0:
        return False

    for sel in selected:
        if sel.slot == candidate.slot and sel.location == candidate.location:
            shared = len(candidate.eligible_players & sel.eligible_players)
            union = len(candidate.eligible_players | sel.eligible_players)
            if union > 0 and shared / union >= _OVERFLOW_CONFLICT_THRESHOLD:
                return False

    return True


def _track_near_miss(
    near_misses: dict[str, tuple[CandidateSession, str]],
    candidate: CandidateSession,
    reason: str,
) -> None:
    """Update the near-miss record for a skipped candidate's game.

    Retains only the highest-scoring skipped candidate per game so the
    suggestions list surfaces the most promising alternative for each
    unscheduled game.

    Args:
        near_misses (dict[str, tuple[CandidateSession, str]]): Running map
            of game id to ``(best_candidate, skip_reason)`` pairs.
        candidate (CandidateSession): The skipped candidate.
        reason (str): Human-readable explanation for why it was skipped.
    """
    gid = candidate.game
    if (
        gid not in near_misses
        or candidate.viability_score > near_misses[gid][0].viability_score
    ):
        near_misses[gid] = (candidate, reason)


def select_sessions(
    candidates: list[CandidateSession],
    config: SchedulerConfig,
    conflict_matrix: dict[tuple[str, str], int],
    all_players: set[str],
) -> SelectionResult:
    """Greedy-pick the best non-conflicting candidates.

    Iterates viable candidates in Layer-1 score order and enforces:
    - Table capacity per (location, slot) with smart overflow
    - Max repeats per game per week
    - Single copy per game per slot
    - Coverage bonus for sessions serving uncovered players
    - Conflict penalty for shared players at the same slot
    - Diminishing-returns diversity multiplier for repeated games

    Smart overflow: when a slot already has one session, a second table
    is allowed only if the game would otherwise go entirely unscheduled
    and the player overlap with the existing session is low.

    Args:
        candidates (list[CandidateSession]): Scored candidates from Layer 1.
        config (SchedulerConfig): Scheduler configuration (repeat limits,
            table ceiling, etc.).
        conflict_matrix (dict[tuple[str, str], int]): Pairwise shared-player
            counts between games.
        all_players (set[str]): Complete set of all player IDs.

    Returns:
        SelectionResult: Selected sessions and near-miss suggestions.
    """
    viable = [c for c in candidates if c.viable]

    selected: list[CandidateSession] = []
    # (location, slot) → number of tables already booked
    occupied: dict[tuple[str, str], int] = {}
    covered_players: set[str] = set()
    game_counts: dict[str, int] = {}
    # game → set of slots already booked (only one copy per slot)
    game_slots: dict[str, set[str]] = {}
    # Best skipped candidate per unscheduled game (for suggestions)
    near_misses: dict[str, tuple[CandidateSession, str]] = {}

    for candidate in viable:
        loc_slot = (candidate.location, candidate.slot)
        tables = occupied.get(loc_slot, 0)

        # Hard: absolute table ceiling
        if tables >= config.max_tables_per_slot:
            if game_counts.get(candidate.game, 0) == 0:
                _track_near_miss(
                    near_misses,
                    candidate,
                    f"All tables at {candidate.location} on {candidate.slot} were full",
                )
            continue

        # Hard: repeat limit
        if game_counts.get(candidate.game, 0) >= config.max_repeats_per_week:
            continue

        # Hard: same game cannot run at the same slot (single copy)
        if candidate.slot in game_slots.get(candidate.game, set()):
            continue

        # Smart overflow: slot already has a session — only allow a second
        # table when the game would otherwise be left out entirely and the
        # player conflict with the existing session is low.
        is_overflow = False
        if tables >= 1:
            if not _qualifies_for_overflow(candidate, game_counts, selected):
                if game_counts.get(candidate.game, 0) == 0:
                    _track_near_miss(
                        near_misses,
                        candidate,
                        f"Could play at {candidate.slot} / {candidate.location} "
                        f"but too much player overlap with the existing session",
                    )
                continue
            is_overflow = True

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
        diversity_mult = 1.0 / (2**game_count)

        adjusted = (
            candidate.viability_score * diversity_mult
            + 0.3 * coverage_bonus
            - 0.2 * conflict_penalty
        )

        # Accept if adjusted score is positive (or schedule is still empty)
        if adjusted > 0 or not selected:
            candidate.is_overflow = is_overflow
            selected.append(candidate)
            occupied[loc_slot] = occupied.get(loc_slot, 0) + 1
            covered_players.update(candidate.eligible_players)
            game_counts[candidate.game] = game_count + 1
            game_slots.setdefault(candidate.game, set()).add(candidate.slot)
        else:
            if game_counts.get(candidate.game, 0) == 0:
                _track_near_miss(
                    near_misses,
                    candidate,
                    f"Score too low after adjustments at "
                    f"{candidate.slot} / {candidate.location}",
                )

    # Present in time-slot order
    selected.sort(key=lambda c: c.slot)

    # Build suggestions for games that got zero sessions
    scheduled_games = set(game_counts.keys())
    suggestions: list[CandidateSession] = []
    for game_id, (cand, reason) in near_misses.items():
        if game_id not in scheduled_games:
            cand.suggestion_reason = reason
            suggestions.append(cand)
    suggestions.sort(key=lambda c: -c.viability_score)

    return SelectionResult(selected=selected, suggestions=suggestions)
