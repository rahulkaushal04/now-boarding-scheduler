"""Entity construction and derived-index computation from poll DataFrames."""

from collections import defaultdict

import pandas as pd

from config import EXCLUDED_COLUMNS
from models.entities import Game, Location, Player, Slot
from utils.names import extract_courtesy_owner, find_best_match


def _data_columns(df: pd.DataFrame) -> list[str]:
    """Return non-metadata columns from a poll DataFrame.

    Excludes the 'Name' and 'Total' columns, which are administrative
    rather than data-bearing.

    Args:
        df (pd.DataFrame): Poll DataFrame with at least a 'Name' column.

    Returns:
        list[str]: Column names excluding EXCLUDED_COLUMNS.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame(columns=["Name", "GameA", "Total"])
        >>> _data_columns(df)
        ['GameA']
    """
    return [c for c in df.columns if c not in EXCLUDED_COLUMNS]


# ---------------------------------------------------------------------------
# Entity builders
# ---------------------------------------------------------------------------


def build_players(
    heavy_df: pd.DataFrame,
    medium_df: pd.DataFrame,
    timings_df: pd.DataFrame,
    place_df: pd.DataFrame,
) -> dict[str, Player]:
    """Construct Player objects from poll DataFrames.

    Args:
        heavy_df (pd.DataFrame): Heavy game poll data.
        medium_df (pd.DataFrame): Medium game poll data.
        timings_df (pd.DataFrame): Timings poll data.
        place_df (pd.DataFrame): Location poll data.

    Returns:
        dict[str, Player]: Mapping of player name to Player object.
    """
    players: dict[str, Player] = {}

    def _get(name: str) -> Player:
        """Return the existing Player for *name*, creating one if needed."""
        if name not in players:
            players[name] = Player(id=name)
        return players[name]

    def _add_game_prefs(df: pd.DataFrame, pref_attr: str) -> None:
        """Populate game preferences on all players from a poll DataFrame.

        Reads each row's voted games, strips the courtesy-owner suffix from
        column headers, and adds the base game name to the player's preference
        set and to ``all_prefs`` for cross-weight-class lookups.

        Args:
            df (pd.DataFrame): Game poll data with boolean vote columns.
            pref_attr (str): Attribute name on Player to populate
                (``"heavy_prefs"`` or ``"medium_prefs"``).
        """
        if df.empty or "Name" not in df.columns:
            return
        game_cols = _data_columns(df)
        # Precompute base names to avoid repeated regex per row
        col_bases = {col: extract_courtesy_owner(col)[0] for col in game_cols}
        for _, row in df.iterrows():
            player = _get(str(row["Name"]))
            prefs: set[str] = getattr(player, pref_attr)
            for col in game_cols:
                if row[col]:
                    base = col_bases[col]
                    prefs.add(base)
                    player.all_prefs.add(base)

    _add_game_prefs(heavy_df, "heavy_prefs")
    _add_game_prefs(medium_df, "medium_prefs")

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
    players: dict[str, Player],
    default_min_players: int = 1,
) -> dict[str, Game]:
    """Construct Game objects from poll CSVs.

    Args:
        heavy_df (pd.DataFrame): Heavy game poll data.
        medium_df (pd.DataFrame): Medium game poll data.
        players (dict[str, Player]): Pre-built player mapping for owner
            resolution.
        default_min_players (int): Default minimum players needed per game.

    Returns:
        dict[str, Game]: Mapping of game name to Game object.
    """
    games: dict[str, Game] = {}
    player_names = list(players)

    def _add_games(df: pd.DataFrame, weight_class: str) -> None:
        """Parse game columns from a poll DataFrame and register them.

        Extracts the base game name and optional courtesy owner from each
        column header, then fuzzy-matches the owner name against known players.

        Args:
            df (pd.DataFrame): Game poll data.
            weight_class (str): Weight category to assign to parsed games.
        """
        if df.empty:
            return
        for col in _data_columns(df):
            base, courtesy = extract_courtesy_owner(col)
            owner = find_best_match(courtesy, player_names) if courtesy else None
            games[base] = Game(
                id=base,
                weight_class=weight_class,
                owner=owner,
                min_players=default_min_players,
            )

    _add_games(heavy_df, "heavy")
    _add_games(medium_df, "medium")

    return games


def build_slots(timings_df: pd.DataFrame) -> dict[str, Slot]:
    """Construct Slot objects from timing columns.

    Parses each timing column header (e.g. ``"Tuesday, 6 PM"``) into a
    day and time component using the first comma as a delimiter.

    Args:
        timings_df (pd.DataFrame): Timings poll DataFrame.

    Returns:
        dict[str, Slot]: Mapping of slot ID to Slot object.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame(columns=["Name", "Tuesday, 6 PM"])
        >>> slots = build_slots(df)
        >>> slots["Tuesday, 6 PM"].day
        'Tuesday'
    """
    if timings_df.empty:
        return {}

    slots: dict[str, Slot] = {}
    for col in _data_columns(timings_df):
        day, _, time_str = col.partition(",")
        slots[col] = Slot(id=col, day=day.strip(), time=time_str.strip())

    return slots


def build_locations(place_df: pd.DataFrame) -> dict[str, Location]:
    """Construct Location objects from place columns.

    Args:
        place_df (pd.DataFrame): Location poll DataFrame.

    Returns:
        dict[str, Location]: Mapping of location ID to Location object.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame(columns=["Name", "HSR Layout"])
        >>> build_locations(df)
        {'HSR Layout': Location(id='HSR Layout')}
    """
    if place_df.empty:
        return {}

    return {col: Location(id=col) for col in _data_columns(place_df)}


# ---------------------------------------------------------------------------
# Derived indices
# ---------------------------------------------------------------------------


def build_overlap_map(
    players: dict[str, Player],
    games: dict[str, Game],
    slots: dict[str, Slot],
    locations: dict[str, Location],
) -> dict[tuple[str, str, str], set[str]]:
    """Compute eligible players per (game, slot, location) triple.

    Pre-indexes players by each dimension so the inner loop performs
    set intersections instead of per-player predicate checks.

    Args:
        players (dict[str, Player]): All known players.
        games (dict[str, Game]): All known games.
        slots (dict[str, Slot]): All known time slots.
        locations (dict[str, Location]): All known venues.

    Returns:
        dict[tuple[str, str, str], set[str]]: Mapping of
            ``(game_id, slot_id, location_id)`` to the set of eligible
            player ids.
    """
    # Pre-index players by each dimension for fast intersection
    game_players: dict[str, set[str]] = {
        gid: {pid for pid, p in players.items() if gid in p.all_prefs} for gid in games
    }
    slot_players: dict[str, set[str]] = {
        sid: {pid for pid, p in players.items() if sid in p.time_availability}
        for sid in slots
    }
    loc_players: dict[str, set[str]] = {
        lid: {pid for pid, p in players.items() if lid in p.location_prefs}
        for lid in locations
    }

    return {
        (game_id, slot_id, loc_id): (
            game_players[game_id] & slot_players[slot_id] & loc_players[loc_id]
        )
        for game_id in games
        for slot_id in slots
        for loc_id in locations
    }


def build_demand_matrix(
    players: dict[str, Player],
) -> dict[str, set[str]]:
    """Map each game to the set of players who want it.

    Args:
        players (dict[str, Player]): All known players.

    Returns:
        dict[str, set[str]]: Mapping of game id to interested player ids.

    Example:
        >>> from models.entities import Player
        >>> p = Player(id="Alice", all_prefs={"Scythe"})
        >>> build_demand_matrix({"Alice": p})
        {'Scythe': {'Alice'}}
    """
    demand: dict[str, set[str]] = defaultdict(set)

    for pid, player in players.items():
        for game in player.all_prefs:
            demand[game].add(pid)

    return dict(demand)


def build_conflict_matrix(
    demand_matrix: dict[str, set[str]],
) -> dict[tuple[str, str], int]:
    """Compute shared-player counts between all game pairs.

    Only pairs with at least one shared player are stored. Both orderings
    of each pair are inserted so lookups can use either key order.

    Args:
        demand_matrix (dict[str, set[str]]): Mapping of game id to interested
            player ids.

    Returns:
        dict[tuple[str, str], int]: Mapping of ``(game_a, game_b)`` to the
            number of players interested in both games.

    Example:
        >>> dm = {"A": {"Alice", "Bob"}, "B": {"Bob", "Carol"}}
        >>> build_conflict_matrix(dm)[("A", "B")]
        1
    """
    conflicts: dict[tuple[str, str], int] = {}
    game_ids = list(demand_matrix)

    for i, g1 in enumerate(game_ids):
        for g2 in game_ids[i + 1 :]:
            shared = len(demand_matrix[g1] & demand_matrix[g2])
            if shared:
                conflicts[(g1, g2)] = shared
                conflicts[(g2, g1)] = shared

    return conflicts
