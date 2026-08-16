"""Step 4 — Insights: what the schedule means for the business.

Three focused views, each answering a question a café owner would
actually ask: which games are we failing to serve, how are the two
cafés doing relative to each other, and who got nothing this week.
No chart is included unless it changes what the owner would do next.
"""

from collections import defaultdict

import pandas as pd
import streamlit as st

from models.config_model import SchedulerConfig
from models.entities import CandidateSession, Game, Location, Player, Slot
from ui.styles import page_header, section_heading


def render_insights(
    players: dict[str, Player],
    games: dict[str, Game],
    demand_matrix: dict[str, set[str]],
    locations: dict[str, Location],
    slots: dict[str, Slot],
    selected: list[CandidateSession],
    config: SchedulerConfig,
) -> None:
    """Render the Insights page.

    Args:
        players: Player objects keyed by id.
        games: Game objects keyed by id (used only to confirm a game exists).
        demand_matrix: Mapping from game id to the set of interested player ids.
        locations: Location objects keyed by id.
        slots: Slot objects keyed by id — used to size table capacity.
        selected: The scheduled sessions for the week.
        config: Scheduler configuration (table capacity per location).
    """
    page_header("Insights", "What this week's schedule means, and where the gaps are.")

    if not players or not demand_matrix:
        st.markdown(
            '<div class="notice-box">Nothing to show yet — go back and build a schedule first.</div>',
            unsafe_allow_html=True,
        )
        return

    sessions_by_game: dict[str, list[CandidateSession]] = defaultdict(list)
    for c in selected:
        sessions_by_game[c.game].append(c)

    # ---- 1. Game demand: who wants what, and who's actually getting it ----
    section_heading("Game demand")
    demand_rows = []
    for gid, interested in demand_matrix.items():
        if not interested:
            continue
        game_sessions = sessions_by_game.get(gid, [])
        served: set[str] = set()
        for c in game_sessions:
            served |= c.assigned_players
        demand_rows.append(
            {
                "Game": gid,
                "Interested": len(interested),
                "Scheduled": len(game_sessions),
                "Served": len(served),
                "Not served": len(interested) - len(served),
            }
        )
    demand_rows.sort(key=lambda r: -r["Interested"])

    if demand_rows:
        st.dataframe(
            pd.DataFrame(demand_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Interested": st.column_config.NumberColumn("Interested", help="Voted for this game"),
                "Scheduled": st.column_config.NumberColumn("Sessions this week"),
                "Served": st.column_config.NumberColumn("Got a seat"),
                "Not served": st.column_config.NumberColumn("Missed out"),
            },
        )

    # ---- 2. HSR vs Jayanagar ----
    section_heading("HSR vs Jayanagar")
    n_slots = max(len(slots), 1)
    location_rows = []
    for lid in locations:
        prefer_count = sum(1 for p in players.values() if lid in p.location_prefs)
        sessions_here = [c for c in selected if c.location == lid]
        capacity = config.table_capacity(lid) * n_slots
        used = len(sessions_here)
        pct_full = round(used / capacity * 100) if capacity else 0
        location_rows.append(
            {
                "Location": lid,
                "Prefer this café": prefer_count,
                "Sessions this week": used,
                "Table capacity": capacity,
                "% of capacity used": pct_full,
            }
        )

    if location_rows:
        st.dataframe(
            pd.DataFrame(location_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "% of capacity used": st.column_config.ProgressColumn(
                    "% of capacity used", min_value=0, max_value=100, format="%d%%"
                ),
            },
        )

    # ---- 3. Players without a session ----
    served_players = {p for c in selected for p in c.assigned_players}
    unserved_players = sorted(set(players) - served_players)

    section_heading("Players without a session")
    if unserved_players:
        st.markdown(
            f'<div class="section-note">{len(unserved_players)} of {len(players)} players '
            "didn't get a seat this week — worth a personal follow-up.</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"Show {len(unserved_players)} players"):
            st.write(", ".join(unserved_players))
    else:
        st.markdown(
            '<div class="section-note">Everyone who voted got a seat this week.</div>',
            unsafe_allow_html=True,
        )
