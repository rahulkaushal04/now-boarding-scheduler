"""Step 4 — Insights: what this week's schedule actually did.

Poll votes are interest, not confirmed attendance — people who say
they're free on Tuesday often don't show. So this page sticks to what's
actually verifiable: the schedule the tool produced and how it's using
the two cafés. It does not forecast demand or recommend spending money
based on vote counts, because that certainty doesn't exist in the data.
"""

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
        games: Game objects keyed by id.
        demand_matrix: Mapping from game id to the set of interested player ids
            (used only to size "games with any votes" for the summary line).
        locations: Location objects keyed by id.
        slots: Slot objects keyed by id — used to size table capacity.
        selected: The scheduled sessions for the week.
        config: Scheduler configuration (table capacity per location).
    """
    page_header("Insights", "How this week's schedule is using your two cafés.")

    if not players:
        st.markdown(
            '<div class="notice-box">Nothing to show yet — go back and build a schedule first.</div>',
            unsafe_allow_html=True,
        )
        return

    games_running = {c.game for c in selected}
    games_with_votes = {g for g, voters in demand_matrix.items() if voters}
    st.markdown(
        f'<div class="confirm-line">This week\'s schedule runs '
        f"<strong>{len(selected)}</strong> session{'s' if len(selected) != 1 else ''} "
        f"across <strong>{len(games_running)} of {len(games_with_votes)}</strong> "
        "games with votes.</div>",
        unsafe_allow_html=True,
    )

    # ---- Table usage: HSR vs Jayanagar ----
    section_heading("Table usage")
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
                f'<div class="rec-card-meta">{prefer_count} players said they prefer '
                "this café</div></div>",
                unsafe_allow_html=True,
            )

    # ---- Players without a session ----
    served_players = {p for c in selected for p in c.assigned_players}
    unserved_players = sorted(set(players) - served_players)

    section_heading("Players without a session")
    if unserved_players:
        st.markdown(
            f'<div class="section-note">{len(unserved_players)} of {len(players)} players '
            "weren't matched to a session based on their votes.</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"Show {len(unserved_players)} players"):
            st.write(", ".join(unserved_players))
    else:
        st.markdown(
            '<div class="section-note">Every player who voted was matched to a session.</div>',
            unsafe_allow_html=True,
        )
