"""Step 2 — Game Rules Editor.

Displays an editable table (one row per discovered game) where the user
can set min/max players, owner, allowed days, and location lock.
Includes visual diff indicators for changed games and per-game / global
reset-to-defaults buttons.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ui.styles import TEXT_SEC
from models.entities import Game, Location, Player, Slot

_DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _values_differ(a: Any, b: Any) -> bool:
    """Safely compare two scalar values, handling ``NaN`` and type mismatches."""
    if pd.isna(a) and pd.isna(b):
        return False
    if pd.isna(a) or pd.isna(b):
        return True
    return str(a) != str(b)


def _game_differs(current: Game | None, original: Game | None) -> bool:
    """Return *True* if any editable field differs between two ``Game`` objects."""
    if current is None or original is None:
        return current is not original
    return (
        current.min_players != original.min_players
        or current.max_players != original.max_players
        or current.owner != original.owner
        or current.allowed_days != original.allowed_days
        or current.location_lock != original.location_lock
    )


def _day_sort_key(day: str) -> int:
    """Return a sort index for *day* so weekdays appear in calendar order."""
    try:
        return _DAY_ORDER.index(day)
    except ValueError:
        return 99


def render_game_rules(
    games: dict[str, Game],
    players: dict[str, Player],
    slots: dict[str, Slot],
    locations: dict[str, Location],
    original_games: dict[str, Game] | None = None,
) -> dict[str, Game]:
    """Render the Game Rules editor and return the updated ``games`` dict.

    Args:
        games: Current game rules (may include prior user edits).
        players: All known players keyed by id.
        slots: All discovered time slots.
        locations: All discovered locations.
        original_games: Auto-detected defaults for visual diff comparison
            and the *Reset* buttons.  Falls back to *games* when ``None``.
    """
    if original_games is None:
        original_games = games

    st.header("Game Rules")
    st.markdown(
        f"<span style='color:{TEXT_SEC}'>"
        "Here you can set who owns each game, which days it can be played, "
        "and where it should be played. Owners detected from the data are "
        "already filled in for you."
        "</span>",
        unsafe_allow_html=True,
    )

    # Check if current games differ from originals (prior edits survived nav)
    has_prior_changes = any(
        _game_differs(games.get(gid), original_games.get(gid)) for gid in original_games
    )
    if has_prior_changes:
        if st.button("Reset All to Defaults", type="secondary"):
            st.session_state.pop("rules_editor", None)
            st.session_state.pop("rules_games", None)
            st.rerun()

    player_names = sorted(players)
    location_names = sorted(locations)
    discovered_days = sorted(
        {s.day for s in slots.values()},
        key=_day_sort_key,
    )

    # Build rows for the editor DataFrame
    rows: list[dict[str, Any]] = []
    for gid in sorted(games):
        g = games[gid]
        row: dict[str, Any] = {
            "Game Name": gid,
            "Weight Class": g.weight_class.capitalize(),
            "Min Players": g.min_players,
            "Max Players": g.max_players,
            "Owner": g.owner or "None",
            "Location": g.location_lock or "Any",
        }
        for day in discovered_days:
            row[day] = day in g.allowed_days if g.allowed_days is not None else True
        rows.append(row)

    edit_df = pd.DataFrame(rows)

    column_config: dict[str, Any] = {
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
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        key="rules_editor",
    )

    # ------------------------------------------------------------------
    # Visual diff: compare the *edited* output against original defaults
    # ------------------------------------------------------------------
    # Build reference DataFrame from original_games for comparison
    orig_rows: list[dict[str, Any]] = []
    for gid in sorted(original_games):
        og = original_games[gid]
        orow: dict[str, Any] = {
            "Game Name": gid,
            "Weight Class": og.weight_class.capitalize(),
            "Min Players": og.min_players,
            "Max Players": og.max_players,
            "Owner": og.owner or "None",
            "Location": og.location_lock or "Any",
        }
        for day in discovered_days:
            orow[day] = day in og.allowed_days if og.allowed_days is not None else True
        orig_rows.append(orow)

    orig_df = pd.DataFrame(orig_rows)

    skip_cols = {"Game Name", "Weight Class"}
    modified: dict[str, tuple[int, list[str]]] = {}
    for idx in range(min(len(orig_df), len(edited))):
        orig_row = orig_df.iloc[idx]
        edit_row = edited.iloc[idx]
        gname = orig_row["Game Name"]
        changes = [
            col
            for col in orig_df.columns
            if col not in skip_cols and _values_differ(orig_row[col], edit_row[col])
        ]
        if changes:
            modified[gname] = (idx, changes)

    if modified:
        count = len(modified)
        st.markdown(
            '<div class="rules-changes-bar">'
            '<span class="rules-changes-count">'
            f'{count} game{"s" if count != 1 else ""} '
            "changed from defaults"
            "</span></div>",
            unsafe_allow_html=True,
        )

        for gname, (row_idx, changed_cols) in modified.items():
            tags_html = " ".join(
                f'<span class="change-tag">{col}</span>' for col in changed_cols
            )
            c_name, c_tags, c_btn = st.columns([3, 5, 1.5])
            with c_name:
                st.markdown(f"**{gname}**")
            with c_tags:
                st.markdown(tags_html, unsafe_allow_html=True)
            with c_btn:
                if st.button(
                    "Reset",
                    key=f"reset_{gname}",
                    use_container_width=True,
                ):
                    # Restore this game to original defaults in rules_games
                    rules = st.session_state.get("rules_games", {})
                    if gname in original_games:
                        rules[gname] = original_games[gname]
                        st.session_state["rules_games"] = rules
                    st.session_state.pop("rules_editor", None)
                    st.rerun()

    # Convert edited table back to Game objects
    updated_games: dict[str, Game] = {}
    for _, row in edited.iterrows():
        gid: str = row["Game Name"]
        original = games.get(gid)
        weight = original.weight_class if original else "medium"

        owner: str | None = row["Owner"]
        if owner == "None" or pd.isna(owner):
            owner = None

        loc: str | None = row["Location"]
        if loc == "Any" or pd.isna(loc):
            loc = None

        allowed = {day for day in discovered_days if row.get(day, True)}
        # All days selected ⇒ no restriction
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
