"""Layer 2 — exact global optimization via mixed-integer linear programming.

Formulates session selection as an assignment problem and solves it as a
sequence of lexicographically-ordered MILPs (SciPy's HiGHS backend), each
solved to a proven optimum. This is the *only* place scheduling decisions
are made — Layer 1 (``engine/scorer.py``) only filters out physically
impossible candidates and computes a display-only ranking score.

Decision variables
-------------------
- ``x_c`` (binary): session ``c = (game, slot, location)`` runs.
- ``z_{c,p}`` (binary, sparse — only defined where ``p`` is in ``c``'s
  eligible-player pool): player ``p`` is actually assigned to attend
  session ``c``.
- ``y_p`` (relaxed to ``[0, 1]``, forced integral by the objective):
  player ``p`` is served by at least one session this week.
- ``w_g`` (relaxed to ``[0, 1]``, forced integral by the objective): game
  ``g`` runs at least once this week.

Splitting "eligible" (``x`` / the candidate's demand pool) from "actually
assigned" (``z``) is what lets the model represent a real physical fact
the score-only heuristic could never enforce exactly: a customer is one
person and can only be at one table at a time. Two sessions running at
the same slot with overlapping fan bases are no longer arbitrarily
forbidden or allowed by a Jaccard-similarity cutoff — the assignment
variables simply split the shared audience between them, and the model
only opens the second table when doing so is actually worth it.

Hard constraints (Tier 1 — never violated)
-------------------------------------------
1. Table ceiling per (slot, location), from ``config.table_capacity``.
2. Repeat limit per game, from ``config.max_repeats_per_week``.
3. One physical copy of a game can run at most once per slot, across
   *all* locations (it can't be in two places, or two tables of the same
   room, at once).
4. One physical copy of a game can't be used at two different locations
   on the *same day*, even across different slots (no same-day transport
   between cafés).
5. A player can be assigned to at most one session per slot (one person,
   one table, at a time).
6. A player is assigned to a given game at most once across the whole
   week, even when that game repeats at several slots. Someone who has
   already played a game once has essentially no real chance of coming
   back to play the *same* game again days later — repeat sessions of a
   popular game exist to reach fans who couldn't make the first slot,
   not to double-book the same person. (Attending a *different* game on
   a different day is unaffected — that's a legitimate repeat customer
   visit and is exactly what the revenue tier rewards.)
7. A session's actually-assigned attendance must clear the game's
   ``min_players`` floor whenever it runs — checked against the real
   post-conflict assignment, not just the raw eligible-pool size.
8. A game's owner, if any, must be assigned to every session of their
   own game (they're required for it to run at all).

Objective — lexicographic business-value hierarchy (Tier 2 → Tier 4)
----------------------------------------------------------------------
Solved as 6 sequential MILPs, each optimizing one tier without ever
regressing an earlier (strictly higher-priority) tier's optimum:

1. **Coverage** (Tier 2a): maximize distinct customers served
   (``sum y_p``). This is the primary growth signal and, as a side
   effect, is what makes the schedule vary across games in the first
   place — covering more distinct people requires running games that
   reach people the already-scheduled sessions don't.
2. **Revenue** (Tier 2b): maximize total attendance, weighted by
   ``config.revenue_weight`` per game weight-class — a per-head revenue
   proxy (no price data exists in the poll CSVs; see module docstring
   in ``models/config_model.py``). Table utilization is not modeled as
   a separate tier because it's strictly dominated by this one: an
   idle table can only ever add zero to this sum, never help it.
3. **Demand match** (Tier 3): maximize the total raw vote count of
   *which* games get scheduled (``sum demand(g) * w_g``) — among
   schedules already tied on coverage and revenue, prefer ones that
   include the games more of the whole group actually voted for.
4. **Variety** (Tier 4): maximize the count of distinct games scheduled
   (``sum w_g``) — breaking ties toward a broader spread of games.
5. **Parsimony**: among schedules that already match every tier above,
   minimize the total number of sessions run (``sum x_c``). Without this,
   the final tie-break below — which must put *some* positive weight on
   every ``x_c`` to get a fully deterministic answer — would have a
   standing incentive to switch on any session that's "free" (doesn't
   cost anything on tiers 1-4), including a pointless duplicate of a
   game already running elsewhere. This stage removes that incentive:
   an idle table stays idle unless running it demonstrably helps a real
   business tier.
6. **Deterministic tie-break**: a tiny canonical-order perturbation on
   ``x`` and ``z`` (see ``candidate_sort_key``) so that even if several
   schedules are still exactly tied on every tier above, the solver
   always lands on the same one — independent of upload order, column
   order, or anything else that carries no real-world meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from models.config_model import SchedulerConfig
from models.entities import CandidateSession, Game

# Solve to a proven optimum, not an accepted gap — the instance is small
# enough (tens to a few hundred binaries) that this stays well under a
# minute even across all five stages.
_MIP_REL_GAP = 0.0
_TIME_LIMIT_SECONDS = 60.0

# Tie-break magnitudes for the final stage. Chosen so that even the sum
# of every possible tie-break term stays far below 1 — the smallest
# possible gap between two different values of any real (integer-valued)
# business-tier objective — so this stage can only ever decide among
# solutions already tied on coverage, revenue, demand match, and variety.
# (Linear, not exponential, priority spacing: like the rest of this
# module's tie-breaks, this collapses the overwhelming majority of ties
# but isn't a formal guarantee against every pathological subset-sum
# coincidence. Any residual tie is still resolved deterministically,
# since HiGHS itself is deterministic for a fixed input problem.)
_TIE_BREAK_EPS_X = 1e-6
_TIE_BREAK_EPS_Z = 1e-9

_DAY_ORDER: dict[str, int] = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def _day_of(slot_id: str) -> str:
    """Extract the weekday name from a ``"Weekday, Time"`` slot id."""
    return slot_id.partition(",")[0].strip()


def candidate_sort_key(candidate: CandidateSession) -> tuple[int, str, str, str]:
    """Deterministic sort/tie-break key independent of upload/column order.

    Column order in the uploaded poll CSVs carries no real-world meaning,
    so it must never influence which of several equally-good candidates is
    preferred. This key breaks ties using the session's own identity
    instead: chronological slot, then location name, then game name.

    Args:
        candidate (CandidateSession): Candidate to derive a key for.

    Returns:
        tuple[int, str, str, str]: ``(day_index, time, location, game)``.

    Example:
        >>> from models.entities import CandidateSession
        >>> c = CandidateSession(game="Scythe", slot="Tuesday, 6 PM", location="HSR")
        >>> candidate_sort_key(c)[0]
        1
    """
    day, _, time_part = candidate.slot.partition(",")
    return (
        _DAY_ORDER.get(day.strip(), 99),
        time_part.strip(),
        candidate.location,
        candidate.game,
    )


@dataclass
class _Index:
    """Variable-index bookkeeping for the MILP's decision variables.

    Layout: ``[x (n_x) | z (n_z) | y (n_y) | w (n_w)]``, each block
    canonically ordered so variable identity never depends on input order.
    """

    candidates: list[CandidateSession]  # canonically ordered, indices 0..n_x-1
    n_x: int
    z_pairs: list[tuple[int, str]]  # (candidate_index, player), canonical order
    z_pos: dict[tuple[int, str], int]
    players: list[str]
    player_pos: dict[str, int]
    games: list[str]
    game_pos: dict[str, int]
    n_vars: int = field(init=False)

    def __post_init__(self) -> None:
        self.n_vars = self.n_x + len(self.z_pairs) + len(self.players) + len(self.games)

    def z_index(self, cand_idx: int, player: str) -> int | None:
        """Return the z variable index for (candidate, player), or None if ineligible."""
        pos = self.z_pos.get((cand_idx, player))
        return None if pos is None else self.n_x + pos

    def y_index(self, player: str) -> int:
        """Return the variable index for player *player*'s coverage indicator."""
        return self.n_x + len(self.z_pairs) + self.player_pos[player]

    def w_index(self, game: str) -> int:
        """Return the variable index for game *game*'s scheduled indicator."""
        return self.n_x + len(self.z_pairs) + len(self.players) + self.game_pos[game]


def _build_index(candidates: list[CandidateSession]) -> _Index:
    """Assign canonical, order-independent indices to all decision variables."""
    ordered = sorted(candidates, key=candidate_sort_key)
    players = sorted({p for c in ordered for p in c.eligible_players})
    games = sorted({c.game for c in ordered})

    z_pairs: list[tuple[int, str]] = []
    for i, c in enumerate(ordered):
        for p in sorted(c.eligible_players):
            z_pairs.append((i, p))
    z_pos = {pair: k for k, pair in enumerate(z_pairs)}

    return _Index(
        candidates=ordered,
        n_x=len(ordered),
        z_pairs=z_pairs,
        z_pos=z_pos,
        players=players,
        player_pos={p: i for i, p in enumerate(players)},
        games=games,
        game_pos={g: i for i, g in enumerate(games)},
    )


class _ConstraintBuilder:
    """Accumulates sparse constraint rows for the shared MILP constraint matrix."""

    def __init__(self, n_vars: int) -> None:
        self._rows: list[int] = []
        self._cols: list[int] = []
        self._data: list[float] = []
        self._lb: list[float] = []
        self._ub: list[float] = []
        self._n_vars = n_vars
        self._r = 0

    def add_row(self, entries: list[tuple[int, float]], low: float, high: float) -> None:
        for col, val in entries:
            self._rows.append(self._r)
            self._cols.append(col)
            self._data.append(val)
        self._lb.append(low)
        self._ub.append(high)
        self._r += 1

    def build(self) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
        A = sparse.csr_matrix(
            (self._data, (self._rows, self._cols)), shape=(self._r, self._n_vars)
        )
        return A, np.array(self._lb), np.array(self._ub)


def _build_constraints(
    idx: _Index,
    config: SchedulerConfig,
    games: dict[str, Game],
) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
    """Build every hard-constraint row shared by all six lexicographic stages."""
    cb = _ConstraintBuilder(idx.n_vars)

    by_slot_loc: dict[tuple[str, str], list[int]] = {}
    by_game: dict[str, list[int]] = {}
    by_game_slot: dict[tuple[str, str], list[int]] = {}
    by_game_day_loc: dict[tuple[str, str, str], list[int]] = {}
    for i, c in enumerate(idx.candidates):
        by_slot_loc.setdefault((c.slot, c.location), []).append(i)
        by_game.setdefault(c.game, []).append(i)
        by_game_slot.setdefault((c.game, c.slot), []).append(i)
        by_game_day_loc.setdefault((c.game, _day_of(c.slot), c.location), []).append(i)

    # 1. Table ceiling per (slot, location) — physical table count.
    for (slot, loc), members in by_slot_loc.items():
        cb.add_row([(i, 1.0) for i in members], 0.0, float(config.table_capacity(loc)))

    # 2. Repeat limit per game — rotation policy.
    for members in by_game.values():
        cb.add_row([(i, 1.0) for i in members], 0.0, float(config.max_repeats_per_week))

    # 3. Single physical copy — a game can run at most once per slot,
    #    across every location at once (it can't be split or duplicated).
    for members in by_game_slot.values():
        if len(members) > 1:
            cb.add_row([(i, 1.0) for i in members], 0.0, 1.0)

    # 4. Day-location exclusivity — a game can't switch cafés within the
    #    same day, even across two different slots on that day.
    by_game_day: dict[tuple[str, str], dict[str, list[int]]] = {}
    for (game, day, loc), members in by_game_day_loc.items():
        by_game_day.setdefault((game, day), {})[loc] = members
    for loc_groups in by_game_day.values():
        locs = sorted(loc_groups)
        for a in range(len(locs)):
            for b in range(a + 1, len(locs)):
                for i in loc_groups[locs[a]]:
                    for j in loc_groups[locs[b]]:
                        cb.add_row([(i, 1.0), (j, 1.0)], 0.0, 1.0)

    # 5. Player-slot exclusivity — one person can attend at most one
    #    session per slot (regardless of location: same time = same body).
    by_player_slot: dict[tuple[str, str], list[int]] = {}
    for k, (i, p) in enumerate(idx.z_pairs):
        slot = idx.candidates[i].slot
        by_player_slot.setdefault((p, slot), []).append(idx.n_x + k)
    for z_indices in by_player_slot.values():
        cb.add_row([(zi, 1.0) for zi in z_indices], 0.0, 1.0)

    # 6. Single-visit-per-game — a player who already played a game once
    #    this week won't realistically come back to play the identical
    #    game again on a different day (unlike attending a *different*
    #    game on a different day, which is a legitimate repeat visit and
    #    stays unrestricted).
    by_player_game: dict[tuple[str, str], list[int]] = {}
    for k, (i, p) in enumerate(idx.z_pairs):
        by_player_game.setdefault((p, idx.candidates[i].game), []).append(idx.n_x + k)
    for z_indices in by_player_game.values():
        if len(z_indices) > 1:
            cb.add_row([(zi, 1.0) for zi in z_indices], 0.0, 1.0)

    # 7. Assignment requires the session to actually run.
    for k, (i, _p) in enumerate(idx.z_pairs):
        cb.add_row([(idx.n_x + k, 1.0), (i, -1.0)], -np.inf, 0.0)

    # 8. Minimum players — real assigned attendance must clear the floor
    #    whenever the session runs (not just the raw eligible-pool size).
    z_by_candidate: dict[int, list[int]] = {}
    for k, (i, _p) in enumerate(idx.z_pairs):
        z_by_candidate.setdefault(i, []).append(idx.n_x + k)
    for i, c in enumerate(idx.candidates):
        game = games.get(c.game)
        min_players = game.min_players if game else 1
        entries = [(zi, 1.0) for zi in z_by_candidate.get(i, [])]
        entries.append((i, -float(min_players)))
        cb.add_row(entries, 0.0, np.inf)

    # 9. Owner must attend every session of their own game.
    for i, c in enumerate(idx.candidates):
        game = games.get(c.game)
        if game is None or game.owner is None:
            continue
        z_owner = idx.z_index(i, game.owner)
        if z_owner is None:
            continue  # scorer already guarantees this shouldn't happen
        cb.add_row([(z_owner, 1.0), (i, -1.0)], 0.0, 0.0)

    # 10. Coverage linkage: y_p <= sum of z_{c,p} over all sessions.
    z_by_player: dict[str, list[int]] = {}
    for k, (i, p) in enumerate(idx.z_pairs):
        z_by_player.setdefault(p, []).append(idx.n_x + k)
    for p in idx.players:
        entries = [(zi, 1.0) for zi in z_by_player.get(p, [])]
        entries.append((idx.y_index(p), -1.0))
        cb.add_row(entries, 0.0, np.inf)

    # 11. Diversity linkage: w_g <= sum of x_c over sessions of game g.
    for g in idx.games:
        entries = [(i, 1.0) for i in by_game.get(g, [])]
        entries.append((idx.w_index(g), -1.0))
        cb.add_row(entries, 0.0, np.inf)

    return cb.build()


def _bounds_and_integrality(idx: _Index) -> tuple[Bounds, np.ndarray]:
    """Return variable bounds and integrality flags.

    ``x`` and ``z`` are binary (real assignment decisions). ``y`` and
    ``w`` stay continuous on ``[0, 1]`` — the standard max-coverage ILP
    relaxation trick: a positive objective coefficient plus an upper
    bound on a sum of binaries forces them to an exact 0/1 value at the
    optimum anyway, without spending extra branch-and-bound effort on them.
    """
    n_binary = idx.n_x + len(idx.z_pairs)
    lb = np.zeros(idx.n_vars)
    ub = np.ones(idx.n_vars)
    integrality = np.zeros(idx.n_vars)
    integrality[:n_binary] = 1
    return Bounds(lb, ub), integrality


def _solve(c_obj, A, lb, ub, bounds, integrality):
    """Run one HiGHS MILP solve and return the raw SciPy result."""
    return milp(
        c=c_obj,
        constraints=LinearConstraint(A, lb, ub),
        integrality=integrality,
        bounds=bounds,
        options={
            "disp": False,
            "mip_rel_gap": _MIP_REL_GAP,
            "time_limit": _TIME_LIMIT_SECONDS,
        },
    )


def _lock_stage(
    A: sparse.csr_matrix,
    lb: np.ndarray,
    ub: np.ndarray,
    coeffs: np.ndarray,
    optimal_value: float,
) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
    """Append a row forcing ``coeffs . vars >= optimal_value`` to the constraint set.

    Used between lexicographic stages so later stages can optimize a new
    objective while never regressing an earlier, higher-priority one.
    """
    A2 = sparse.vstack([A, sparse.csr_matrix(coeffs)]).tocsr()
    lb2 = np.append(lb, optimal_value)
    ub2 = np.append(ub, np.inf)
    return A2, lb2, ub2


def select_optimal(
    candidates: list[CandidateSession],
    config: SchedulerConfig,
    games: dict[str, Game],
    demand_matrix: dict[str, set[str]],
) -> tuple[list[CandidateSession], dict[str, float]]:
    """Solve session selection to global optimality via 6-stage lexicographic MILP.

    See the module docstring for the full formulation. Populates
    ``assigned_players`` / ``assigned_count`` on every returned session
    from the final stage's player-assignment variables.

    Args:
        candidates (list[CandidateSession]): Viable candidates only
            (``viable=True``); non-viable candidates must be filtered out
            by the caller before this is called.
        config (SchedulerConfig): Scheduler configuration (table
            capacity, repeat limit, revenue weights).
        games (dict[str, Game]): Game rules keyed by game id (min_players,
            owner, weight_class) — must cover every game referenced by
            *candidates*.
        demand_matrix (dict[str, set[str]]): Mapping of game id to the
            full set of interested players (used for the Tier 3
            demand-match objective).

    Returns:
        tuple[list[CandidateSession], dict[str, float]]: The selected
            sessions (unordered — the caller is responsible for display
            ordering) and solver diagnostics (per-stage optimal values).

    Raises:
        RuntimeError: If the solver reports no feasible solution at any
            stage. This should not happen in practice, because selecting
            nothing (all x = z = 0) always satisfies every constraint.
    """
    if not candidates:
        return [], {}

    idx = _build_index(candidates)
    A, lb, ub = _build_constraints(idx, config, games)
    bounds, integrality = _bounds_and_integrality(idx)

    def _run(stage_name: str, coeffs: np.ndarray, A_, lb_, ub_):
        c_obj = -coeffs  # milp minimizes; negate to maximize
        res = _solve(c_obj, A_, lb_, ub_, bounds, integrality)
        if res.x is None:
            raise RuntimeError(
                f"Scheduling optimizer found no feasible solution (stage: {stage_name})"
            )
        return res

    # --- Stage 1 (Tier 2a): maximize distinct players covered ---
    c1 = np.zeros(idx.n_vars)
    for p in idx.players:
        c1[idx.y_index(p)] = 1.0
    res1 = _run("coverage", c1, A, lb, ub)
    coverage_opt = round(-res1.fun)
    A, lb, ub = _lock_stage(A, lb, ub, c1, coverage_opt)

    # --- Stage 2 (Tier 2b): maximize revenue-weighted attendance ---
    c2 = np.zeros(idx.n_vars)
    for k, (i, _p) in enumerate(idx.z_pairs):
        game = games.get(idx.candidates[i].game)
        weight = config.revenue_weight(game.weight_class) if game else 1.0
        c2[idx.n_x + k] = weight
    res2 = _run("revenue", c2, A, lb, ub)
    revenue_opt = -res2.fun
    A, lb, ub = _lock_stage(A, lb, ub, c2, revenue_opt)

    # --- Stage 3 (Tier 3): maximize demand-weighted game selection ---
    c3 = np.zeros(idx.n_vars)
    for g in idx.games:
        c3[idx.w_index(g)] = float(len(demand_matrix.get(g, set())))
    res3 = _run("demand match", c3, A, lb, ub)
    demand_match_opt = -res3.fun
    A, lb, ub = _lock_stage(A, lb, ub, c3, demand_match_opt)

    # --- Stage 4 (Tier 4): maximize distinct games scheduled (variety) ---
    c4 = np.zeros(idx.n_vars)
    for g in idx.games:
        c4[idx.w_index(g)] = 1.0
    res4 = _run("variety", c4, A, lb, ub)
    variety_opt = round(-res4.fun)
    A, lb, ub = _lock_stage(A, lb, ub, c4, variety_opt)

    # --- Stage 5: parsimony — minimize total sessions among tier-1..4 ties.
    #     Prevents the tie-break stage below from having any incentive to
    #     switch on a "free" but redundant extra session (see module
    #     docstring). Framed as maximizing -sum(x) to reuse the same
    #     maximize/lock machinery as every other stage.
    c5 = np.zeros(idx.n_vars)
    for i in range(idx.n_x):
        c5[i] = -1.0
    res5 = _run("parsimony", c5, A, lb, ub)
    parsimony_opt = -res5.fun
    A, lb, ub = _lock_stage(A, lb, ub, c5, parsimony_opt)

    # --- Stage 6: deterministic tie-break, canonical order on x then z ---
    c6 = np.zeros(idx.n_vars)
    for i in range(idx.n_x):
        c6[i] = _TIE_BREAK_EPS_X * (idx.n_x - i)
    for k in range(len(idx.z_pairs)):
        c6[idx.n_x + k] = _TIE_BREAK_EPS_Z * (len(idx.z_pairs) - k)
    res6 = _run("tie-break", c6, A, lb, ub)

    x = res6.x[: idx.n_x]
    z_flat = res6.x[idx.n_x : idx.n_x + len(idx.z_pairs)]

    selected: list[CandidateSession] = []
    for i in range(idx.n_x):
        if x[i] <= 0.5:
            continue
        c = idx.candidates[i]
        selected.append(c)
    for k, (i, p) in enumerate(idx.z_pairs):
        if z_flat[k] > 0.5 and x[i] > 0.5:
            idx.candidates[i].assigned_players.add(p)
    for c in selected:
        c.assigned_count = len(c.assigned_players)

    diagnostics = {
        "players_covered": float(coverage_opt),
        "revenue_weighted_attendance": float(revenue_opt),
        "demand_weighted_score": float(demand_match_opt),
        "distinct_games": float(variety_opt),
        "session_count": float(parsimony_opt),
        "total_assigned_attendance": float(sum(c.assigned_count for c in selected)),
        "stage6_status": float(res6.status),
    }
    return selected, diagnostics
