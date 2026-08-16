"""Step 4 — Insights: what the schedule means for the business.

Three direct answers, each one a decision a café owner would actually
make: which specific games have people wanting in who aren't getting a
seat (candidates for a second copy or another session), how the two
cafés compare this week, and who to personally follow up with. Nothing
here is a raw data dump — every number is already the answer, not a
spreadsheet to go figure the answer out from.
"""

from collections import defaultdict

import streamlit as st

from models.config_model import SchedulerConfig
from models.entities import CandidateSession, Game, Location, Player, Slot
from ui.styles import page_header, section_heading

_MAX_GAPS_SHOWN = 5


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
    page_header("Insights", "Where this week's schedule is leaving value on the table.")

    if not players or not demand_matrix:
        st.markdown(
            '<div class="notice-box">Nothing to show yet — go back and build a schedule first.</div>',
            unsafe_allow_html=True,
        )
        return

    sessions_by_game: dict[str, list[CandidateSession]] = defaultdict(list)
    for c in selected:
        sessions_by_game[c.game].append(c)

    # ---- 1. Unmet demand: specific games worth a second copy or session ----
    section_heading("Games people want but can't get into")
    gaps: list[tuple[str, int, int]] = []
    for gid, interested in demand_matrix.items():
        if not interested:
            continue
        served: set[str] = set()
        for c in sessions_by_game.get(gid, []):
            served |= c.assigned_players
        not_served = len(interested) - len(served)
        if not_served > 0:
            gaps.append((gid, not_served, len(interested)))
    gaps.sort(key=lambda r: -r[1])

    if not gaps:
        st.markdown(
            '<div class="section-note">Everyone who wanted a game got a seat this week.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="section-note">Worth a second copy, an extra session, or a bigger table.</div>',
            unsafe_allow_html=True,
        )
        for gid, not_served, interested in gaps[:_MAX_GAPS_SHOWN]:
            st.markdown(
                f'<div class="rec-card"><div class="rec-card-title">{gid}</div>'
                f'<div class="rec-card-meta">{not_served} of {interested} people '
                "who wanted it didn't get a seat</div></div>",
                unsafe_allow_html=True,
            )
        if len(gaps) > _MAX_GAPS_SHOWN:
            with st.expander(f"Show {len(gaps) - _MAX_GAPS_SHOWN} more"):
                for gid, not_served, interested in gaps[_MAX_GAPS_SHOWN:]:
                    st.markdown(f"**{gid}** — {not_served} of {interested} missed out")

    # ---- 2. HSR vs Jayanagar ----
    section_heading("HSR vs Jayanagar")
    n_slots = max(len(slots), 1)
    loc_cols = st.columns(max(len(locations), 1))
    for col, lid in zip(loc_cols, sorted(locations)):
        prefer_count = sum(1 for p in players.values() if lid in p.location_prefs)
        used = sum(1 for c in selected if c.location == lid)
        capacity = config.table_capacity(lid) * n_slots
        pct_full = round(used / capacity * 100) if capacity else 0
        with col:
            st.markdown(
                f'<div class="rec-card"><div class="rec-card-title">{lid}</div>'
                f'<div class="rec-card-meta">{used} of {capacity} tables used this week '
                f"({pct_full}%)</div>"
                f'<div class="rec-card-meta">{prefer_count} players prefer this café</div></div>',
                unsafe_allow_html=True,
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
