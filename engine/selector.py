"""Layer 2 — session selection: exact optimization plus display post-processing.

Delegates the actual decision-making to `engine.optimizer.select_optimal`
(exact MILP optimization) and handles the remaining display-only concerns:
chronological ordering, the "2nd table" overflow badge, and near-miss
suggestions for games that didn't make the schedule.
"""

from models.entities import CandidateSession, Game, SelectionResult
from models.config_model import SchedulerConfig
from engine.optimizer import (
    _DAY_ORDER,
    _day_of,
    candidate_sort_key,
    select_optimal,
)

# Canonical weekday order used to sort the final selected-session list.
# Re-exported for backward compatibility / direct use by callers.
DAY_ORDER = _DAY_ORDER


def _slot_sort_key(slot_id: str) -> tuple[int, str]:
    """Return a (day_index, slot_id) sort key for chronological ordering.

    Slot ids follow the format ``"Weekday, Time"`` (e.g. ``"Tuesday, 6 PM"``).
    Unknown weekday names sort last (index 99).

    Args:
        slot_id (str): Full slot identifier string.

    Returns:
        tuple[int, str]: ``(day_order_index, slot_id)`` for stable ordering.

    Example:
        >>> _slot_sort_key("Tuesday, 6 PM")
        (1, 'Tuesday, 6 PM')
        >>> _slot_sort_key("Friday, 6 PM")
        (4, 'Friday, 6 PM')
    """
    day = slot_id.partition(",")[0].strip()
    return (DAY_ORDER.get(day, 99), slot_id)


def _mark_overflow(selected: list[CandidateSession]) -> None:
    """Flag every non-primary session sharing a (slot, location) as overflow.

    Purely a display concern (drives the "2nd table" badge in the UI) — it
    has no effect on which sessions were selected. Within each occupied
    (slot, location), the session with the most actually-assigned players
    is the "primary" table; any additional co-located session is marked
    overflow. Ties are broken with the same canonical, upload-order-
    independent key used throughout the optimizer, so the flagging is
    fully deterministic.

    Args:
        selected (list[CandidateSession]): Sessions chosen by the optimizer.
            Mutated in place (sets ``is_overflow``).
    """
    groups: dict[tuple[str, str], list[CandidateSession]] = {}
    for c in selected:
        groups.setdefault((c.slot, c.location), []).append(c)

    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(
            group, key=lambda c: (-c.assigned_count, candidate_sort_key(c))
        )
        for c in ordered[1:]:
            c.is_overflow = True


def _final_sort_key(c: CandidateSession) -> tuple:
    """Deterministic display order: chronological, primary table before overflow."""
    return _slot_sort_key(c.slot) + (c.location, c.is_overflow, c.game)


def _suggestion_reason(
    best: CandidateSession,
    selected: list[CandidateSession],
    config: SchedulerConfig,
) -> str:
    """Explain, from the final solution, why a game's best candidate wasn't picked."""
    loc_slot = (best.slot, best.location)
    co_located = [c for c in selected if (c.slot, c.location) == loc_slot]

    if len(co_located) >= config.table_capacity(best.location):
        return f"All tables at {best.location} on {best.slot} were full"

    best_day = _day_of(best.slot)
    other_locations_same_day = {
        c.location
        for c in selected
        if c.game == best.game and _day_of(c.slot) == best_day
    } - {best.location}
    if other_locations_same_day:
        other_loc = sorted(other_locations_same_day)[0]
        return (
            f"{best.game} was already scheduled at {other_loc} on {best_day} — "
            f"the same copy can't move locations within a day"
        )

    repeats = sum(1 for c in selected if c.game == best.game)
    if repeats >= config.max_repeats_per_week:
        return (
            f"{best.game} already reached its cap of "
            f"{config.max_repeats_per_week} session(s) this week"
        )

    return "Didn't make the optimal schedule this week — other sessions served the group better"


def _build_suggestions(
    viable: list[CandidateSession],
    selected: list[CandidateSession],
    config: SchedulerConfig,
) -> list[CandidateSession]:
    """Surface the best candidate for every game that scored zero sessions.

    Args:
        viable (list[CandidateSession]): All viable (pre-optimization)
            candidates.
        selected (list[CandidateSession]): The optimizer's chosen sessions.
        config (SchedulerConfig): Scheduler configuration.

    Returns:
        list[CandidateSession]: One near-miss candidate per unscheduled
            game, each annotated with ``suggestion_reason``, sorted
            best-first.
    """
    scheduled_games = {c.game for c in selected}

    by_game: dict[str, list[CandidateSession]] = {}
    for c in viable:
        by_game.setdefault(c.game, []).append(c)

    suggestions: list[CandidateSession] = []
    for game_id, game_candidates in by_game.items():
        if game_id in scheduled_games:
            continue
        best = sorted(
            game_candidates,
            key=lambda c: (-c.viability_score,) + candidate_sort_key(c),
        )[0]
        best.suggestion_reason = _suggestion_reason(best, selected, config)
        suggestions.append(best)

    suggestions.sort(key=lambda c: -c.viability_score)
    return suggestions


def select_sessions(
    candidates: list[CandidateSession],
    config: SchedulerConfig,
    games: dict[str, Game],
    demand_matrix: dict[str, set[str]],
) -> SelectionResult:
    """Select the best non-conflicting set of sessions for the week.

    Delegates the actual decision to `engine.optimizer.select_optimal`
    (exact 5-stage lexicographic MILP: coverage, then revenue, then
    demand-match, then variety, then a deterministic tie-break — see that
    module's docstring), then adds the display-only post-processing the
    UI depends on: chronological ordering, the "2nd table" overflow
    badge, and near-miss suggestions for games that scored zero sessions.

    Args:
        candidates (list[CandidateSession]): Scored candidates from Layer 1
            (both viable and non-viable; non-viable ones are filtered here).
        config (SchedulerConfig): Scheduler configuration (repeat limits,
            table ceiling, revenue weights).
        games (dict[str, Game]): Game rules keyed by game id (min_players,
            owner, weight_class), forwarded to the optimizer.
        demand_matrix (dict[str, set[str]]): Mapping of game id to
            interested players, forwarded to the optimizer for the
            demand-match objective.

    Returns:
        SelectionResult: Selected sessions and near-miss suggestions.
    """
    viable = [c for c in candidates if c.viable]
    if not viable:
        return SelectionResult()

    selected, _diagnostics = select_optimal(viable, config, games, demand_matrix)

    _mark_overflow(selected)
    selected.sort(key=_final_sort_key)

    suggestions = _build_suggestions(viable, selected, config)

    return SelectionResult(selected=selected, suggestions=suggestions)
