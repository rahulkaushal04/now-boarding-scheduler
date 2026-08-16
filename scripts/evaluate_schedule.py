"""Compute business-value metrics for a schedule run against example_data.

Standalone script (no Streamlit) that runs the full scoring → selection
pipeline against ``example_data`` and prints a metrics summary. Used to
compare algorithm versions on identical input.

Usage:
    python scripts/evaluate_schedule.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import load_game_csv, load_place_csv, load_timings_csv
from data.processor import (
    build_conflict_matrix,
    build_demand_matrix,
    build_games,
    build_locations,
    build_overlap_map,
    build_players,
    build_slots,
)
from engine.scorer import score_all_candidates
from engine.selector import select_sessions
from models.config_model import SchedulerConfig

_EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "example_data"


def main() -> None:
    """Build a schedule from ``example_data`` and print business metrics to stdout.

    Runs the full scoring → selection pipeline with default
    ``SchedulerConfig`` values, then reports sessions, coverage,
    attendance, and unmet demand — the same numbers used to compare
    algorithm versions during development.
    """
    heavy_df, _ = load_game_csv(str(_EXAMPLE_DIR / "heavy_games.csv"), "heavy")
    medium_df, _ = load_game_csv(str(_EXAMPLE_DIR / "medium_games.csv"), "medium")
    timings_df, _ = load_timings_csv(str(_EXAMPLE_DIR / "timings.csv"))
    place_df, _ = load_place_csv(str(_EXAMPLE_DIR / "place.csv"))

    config = SchedulerConfig()
    players = build_players(heavy_df, medium_df, timings_df, place_df)
    games = build_games(heavy_df, medium_df, players, config.default_min_players)
    slots = build_slots(timings_df)
    locations = build_locations(place_df)

    overlap_map = build_overlap_map(players, games, slots, locations)
    demand_matrix = build_demand_matrix(players)
    conflict_matrix = build_conflict_matrix(demand_matrix)
    all_player_ids = set(players)

    candidates = score_all_candidates(
        overlap_map, games, demand_matrix, slots, locations, all_player_ids
    )
    result = select_sessions(candidates, config, games, demand_matrix)

    selected = result.selected
    n_players = len(players)
    n_games = len(games)

    covered_actual = {p for c in selected for p in c.assigned_players}
    covered_demand_pool = {p for c in selected for p in c.eligible_players}
    total_assigned_attendance = sum(c.assigned_count for c in selected)
    total_eligible_pool = sum(c.eligible_count for c in selected)
    distinct_games = {c.game for c in selected}
    by_location: dict[str, int] = {}
    for c in selected:
        by_location[c.location] = by_location.get(c.location, 0) + 1

    unmet = 0
    for gid, fans in demand_matrix.items():
        served = set()
        for c in selected:
            if c.game == gid:
                served |= c.assigned_players
        unmet += len(fans - served)

    print("=" * 60)
    print("SCHEDULE METRICS")
    print("=" * 60)
    print(f"Players (total):                         {n_players}")
    print(f"Games (total):                            {n_games}")
    print(f"Sessions scheduled:                       {len(selected)}")
    print(f"Distinct games scheduled:                 {len(distinct_games)} / {n_games}")
    print(f"Players actually served (unique):         {len(covered_actual)} / {n_players}")
    print(
        f"Players in demand pool of selected games: "
        f"{len(covered_demand_pool)} / {n_players}  (upper bound, not de-duplicated)"
    )
    print(f"Total assigned attendance (revenue proxy): {total_assigned_attendance}")
    print(f"Total eligible-pool sum (double-counts conflicts): {total_eligible_pool}")
    print(f"Sessions per location:                    {dict(sorted(by_location.items()))}")
    print(f"Unmet demand (votes unserved):             {unmet}")
    print(f"Suggestions (unscheduled games):           {len(result.suggestions)}")
    print()
    print("Games scheduled (slot / location / game / assigned (eligible pool)):")
    for c in sorted(selected, key=lambda c: (c.slot, c.location, c.game)):
        print(
            f"  {c.slot:<18} {c.location:<12} {c.game:<40} "
            f"assigned={c.assigned_count} (pool={c.eligible_count})"
        )


if __name__ == "__main__":
    main()
