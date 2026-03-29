"""Step 2 — Game Rules Editor.

Displays an editable table (one row per discovered game) where the owner
can set: min/max players, owner, allowed days, and location lock.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from models.entities import Game
from ui.styles import PRIMARY, ACCENT, TEXT_SEC


def render_game_rules(
    games: dict[str, Game],
    players: dict,
    slots: dict,
    locations: dict,
) -> dict[str, Game]:
    """Render the Game Rules editor and return the updated ``games`` dict.

    Uses ``st.data_editor`` for core fields (min/max players, owner,
    location) and adds boolean checkbox columns for each discovered day.
    """
    st.header("Game Rules")
    st.markdown(
        f"<span style='color:{TEXT_SEC}'>"
        "Set ownership, day restrictions, and location locks per game. "
        "All rules are editable \u2014 auto-detected owners are pre-filled."
        "</span>",
        unsafe_allow_html=True,
    )

    player_names = sorted(players.keys())
    location_names = sorted(locations.keys())
    discovered_days = sorted(
        {s.day for s in slots.values()},
        key=lambda d: [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ].index(d) if d in [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ] else 99,
    )

    # Build rows for the editor DataFrame
    rows: list[dict] = []
    for gid in sorted(games.keys()):
        g = games[gid]
        row: dict = {
            "Game Name": gid,
            "Weight Class": g.weight_class.capitalize(),
            "Min Players": g.min_players,
            "Max Players": g.max_players,
            "Owner": g.owner if g.owner else "None",
            "Location": g.location_lock if g.location_lock else "Any",
        }
        for day in discovered_days:
            # Default: all days allowed (True) unless restricted
            if g.allowed_days is not None:
                row[day] = day in g.allowed_days
            else:
                row[day] = True
        rows.append(row)

    edit_df = pd.DataFrame(rows)

    # Column configuration
    column_config: dict = {
        "Game Name": st.column_config.TextColumn("Game Name", disabled=True),
        "Weight Class": st.column_config.TextColumn("Weight Class", disabled=True),
        "Min Players": st.column_config.NumberColumn(
            "Min Players", min_value=1, max_value=20
        ),
        "Max Players": st.column_config.NumberColumn(
            "Max Players", min_value=1, max_value=20
        ),
        "Owner": st.column_config.SelectboxColumn(
            "Owner", options=["None"] + player_names, required=True
        ),
        "Location": st.column_config.SelectboxColumn(
            "Location", options=["Any"] + location_names, required=True
        ),
    }
    for day in discovered_days:
        column_config[day] = st.column_config.CheckboxColumn(day, default=True)

    edited = st.data_editor(
        edit_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="rules_editor",
    )

    # Convert edited table back to Game objects
    updated_games: dict[str, Game] = {}
    for _, row in edited.iterrows():
        gid = row["Game Name"]
        original = games.get(gid)
        weight = original.weight_class if original else "medium"

        owner = row["Owner"]
        if owner == "None" or pd.isna(owner):
            owner = None

        loc = row["Location"]
        if loc == "Any" or pd.isna(loc):
            loc = None

        allowed: set[str] = set()
        for day in discovered_days:
            if row.get(day, True):
                allowed.add(day)
        # If all days selected → no restriction (None)
        allowed_days = allowed if len(allowed) < len(discovered_days) else None

        updated_games[gid] = Game(
            id=gid,
            weight_class=weight,
            min_players=int(row["Min Players"]),
            max_players=int(row["Max Players"]),
            owner=owner,
            allowed_days=allowed_days,
            location_lock=loc,
        )

    return updated_games
