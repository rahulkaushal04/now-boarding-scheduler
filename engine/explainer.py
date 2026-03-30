"""Explainability layer — human-readable reasoning traces for candidates."""

from models.entities import CandidateSession, Game, SessionReasoning


def explain_candidate(
    candidate: CandidateSession,
    demand_matrix: dict[str, set[str]],
    covered_players: set[str],
    games: dict[str, Game],
    rank: int | None = None,
) -> SessionReasoning:
    """Generate a human-readable reasoning trace for a scored candidate.

    Args:
        candidate (CandidateSession): The candidate session to explain.
        demand_matrix (dict[str, set[str]]): Mapping of game to interested
            players.
        covered_players (set[str]): Players already assigned to a session.
        games (dict[str, Game]): Mapping of game ID to Game object.
        rank (int | None): Optional rank position in the selected list.

    Returns:
        SessionReasoning: Demand, overlap, and selection explanations with a
            copy of the candidate's score breakdown.

    Example:
        >>> from models.entities import CandidateSession
        >>> c = CandidateSession(game="Scythe", slot="Tue 6 PM",
        ...     location="HSR", eligible_players={"Alice"}, eligible_count=1)
        >>> r = explain_candidate(c, {"Scythe": {"Alice"}}, set(), {}, rank=1)
        >>> "Scythe" in r.demand_reason
        True
    """
    interested = demand_matrix.get(candidate.game, set())
    total_interested = len(interested)
    max_demand = max((len(s) for s in demand_matrix.values()), default=0)

    # --- Demand reason ---
    demand_reason = (
        f"{candidate.game} has {total_interested} interested "
        f"player{'s' if total_interested != 1 else ''}"
    )
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
) -> None:
    """Attach conflict notes describing shared players between sessions.

    Mutates the ``reasoning`` attribute of each selected session in place.
    Sessions with no shared players across the schedule are left with
    ``conflict_note`` as ``None``.

    Args:
        selected (list[CandidateSession]): List of selected candidate sessions.

    Example:
        >>> from models.entities import CandidateSession, SessionReasoning
        >>> s1 = CandidateSession(game="G1", slot="S1", location="L1",
        ...     eligible_players={"Alice"},
        ...     reasoning=SessionReasoning("", "", ""))
        >>> s2 = CandidateSession(game="G2", slot="S2", location="L1",
        ...     eligible_players={"Alice"},
        ...     reasoning=SessionReasoning("", "", ""))
        >>> add_conflict_notes([s1, s2])
        >>> s1.reasoning.conflict_note is not None
        True
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
