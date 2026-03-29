from __future__ import annotations

from collections import defaultdict
from typing import Dict, Set, Tuple

import pandas as pd

from models.entities import Game, Location, Player, Slot
from utils.names import extract_courtesy_owner, find_best_match

EXCLUDED_COLUMNS = {"Name", "Total"}


def _data_columns(df: pd.DataFrame) -> list[str]:
    """Return non-excluded columns."""
    return [c for c in df.columns if c not in EXCLUDED_COLUMNS]


# ---------------------------------------------------------------------------
# Entity builders
# ---------------------------------------------------------------------------


def build_players(
    heavy_df: pd.DataFrame,
    medium_df: pd.DataFrame,
    timings_df: pd.DataFrame,
    place_df: pd.DataFrame,
) -> Dict[str, Player]:
    """Construct Player objects from poll DataFrames."""
    players: Dict[str, Player] = {}

    def _get(name: str) -> Player:
        if name not in players:
            players[name] = Player(id=name)
        return players[name]

    # Heavy preferences
    if not heavy_df.empty and "Name" in heavy_df.columns:
        game_cols = _data_columns(heavy_df)
        for _, row in heavy_df.iterrows():
            player = _get(str(row["Name"]))
            for col in game_cols:
                if row[col]:
                    base, _ = extract_courtesy_owner(col)
                    player.heavy_prefs.add(base)
                    player.all_prefs.add(base)

    # Medium preferences
    if not medium_df.empty and "Name" in medium_df.columns:
        game_cols = _data_columns(medium_df)
        for _, row in medium_df.iterrows():
            player = _get(str(row["Name"]))
            for col in game_cols:
                if row[col]:
                    base, _ = extract_courtesy_owner(col)
                    player.medium_prefs.add(base)
                    player.all_prefs.add(base)

    # Time availability
    if not timings_df.empty and "Name" in timings_df.columns:
        slot_cols = _data_columns(timings_df)
        for _, row in timings_df.iterrows():
            player = _get(str(row["Name"]))
            for col in slot_cols:
                if row[col]:
                    player.time_availability.add(col)

    # Location preferences
    if not place_df.empty and "Name" in place_df.columns:
        loc_cols = _data_columns(place_df)
        for _, row in place_df.iterrows():
            player = _get(str(row["Name"]))
            for col in loc_cols:
                if row[col]:
                    player.location_prefs.add(col)

    return players


def build_games(
    heavy_df: pd.DataFrame,
    medium_df: pd.DataFrame,
    players: Dict[str, Player],
) -> Dict[str, Game]:
    """Construct Game objects from poll CSVs."""
    games: Dict[str, Game] = {}
    player_names = list(players)

    def _add_games(df: pd.DataFrame, weight_class: str) -> None:
        if df.empty:
            return
        for col in df.columns:
            if col in EXCLUDED_COLUMNS:
                continue
            base, courtesy = extract_courtesy_owner(col)
            owner: str | None = None
            if courtesy:
                owner = find_best_match(courtesy, player_names)
            games[base] = Game(id=base, weight_class=weight_class, owner=owner)

    _add_games(heavy_df, "heavy")
    _add_games(medium_df, "medium")

    return games


def build_slots(timings_df: pd.DataFrame) -> Dict[str, Slot]:
    """Construct Slot objects from timing columns."""
    slots: Dict[str, Slot] = {}

    if timings_df.empty:
        return slots

    for col in timings_df.columns:
        if col in EXCLUDED_COLUMNS:
            continue

        day, _, time_str = col.partition(",")
        slots[col] = Slot(id=col, day=day.strip(), time=time_str.strip())

    return slots


def build_locations(place_df: pd.DataFrame) -> Dict[str, Location]:
    """Construct Location objects from place columns."""
    locations: Dict[str, Location] = {}

    if place_df.empty:
        return locations

    for col in place_df.columns:
        if col in EXCLUDED_COLUMNS:
            continue
        locations[col] = Location(id=col)

    return locations


# ---------------------------------------------------------------------------
# Derived indices
# ---------------------------------------------------------------------------


def build_overlap_map(
    players: Dict[str, Player],
    games: Dict[str, Game],
    slots: Dict[str, Slot],
    locations: Dict[str, Location],
) -> Dict[Tuple[str, str, str], Set[str]]:
    """Compute eligible players per (game, slot, location)."""
    overlap: Dict[Tuple[str, str, str], Set[str]] = {}

    for game_id in games:
        for slot_id in slots:
            for loc_id in locations:
                eligible = {
                    pid
                    for pid, player in players.items()
                    if (
                        game_id in player.all_prefs
                        and slot_id in player.time_availability
                        and loc_id in player.location_prefs
                    )
                }
                overlap[(game_id, slot_id, loc_id)] = eligible

    return overlap


def build_demand_matrix(
    players: Dict[str, Player],
) -> Dict[str, Set[str]]:
    """Map each game to players who want it."""
    demand: Dict[str, Set[str]] = defaultdict(set)

    for pid, player in players.items():
        for game in player.all_prefs:
            demand[game].add(pid)

    return dict(demand)


def build_conflict_matrix(
    demand_matrix: Dict[str, Set[str]],
) -> Dict[Tuple[str, str], int]:
    """Compute shared-player counts between games."""
    conflicts: Dict[Tuple[str, str], int] = {}
    game_ids = list(demand_matrix)

    for i, g1 in enumerate(game_ids):
        for g2 in game_ids[i + 1 :]:
            shared = len(demand_matrix[g1] & demand_matrix[g2])
            if shared:
                conflicts[(g1, g2)] = shared
                conflicts[(g2, g1)] = shared

    return conflicts
