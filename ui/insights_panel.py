"""Step 4 — Insights & Analytics dashboard.

Renders seven analytic sections using Plotly charts and Streamlit
metrics: game demand ranking, demand heatmap, conflict matrix,
player coverage, location demand split, unviable games, and time-slot
density.  All charts use the ``plotly_dark`` template with brand colours.
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from ui.styles import ACCENT, ALERT, PRIMARY, SUCCESS, SURFACE_RAISED
from models.entities import CandidateSession, Game, Location, Player, Slot


def render_insights(
    candidates: list[CandidateSession],
    players: dict[str, Player],
    games: dict[str, Game],
    demand_matrix: dict[str, set[str]],
    conflict_matrix: dict[tuple[str, str], int],
    slots: dict[str, Slot],
    locations: dict[str, Location],
    overlap_map: dict[tuple[str, str, str], set[str]],
) -> None:
    """Render the full analytics / insights dashboard.

    Args:
        candidates: All candidate sessions (viable and non-viable).
        players: Player objects keyed by id.
        games: Game objects keyed by id.
        demand_matrix: Mapping from game id to the set of interested player ids.
        conflict_matrix: Mapping from ``(game_a, game_b)`` to shared-player count.
        slots: Slot objects keyed by id (order preserved from CSV).
        locations: Location objects keyed by id.
        overlap_map: ``(game, slot, location) → eligible players`` mapping.
    """
    st.header("Insights & Analytics")

    viable = [c for c in candidates if c.viable]
    non_viable = [c for c in candidates if not c.viable]

    # 1. Game Demand Ranking — bar chart
    st.subheader("Game Demand Ranking")
    demand_rows = [
        {"Game": g, "Interested Players": len(pset)}
        for g, pset in sorted(demand_matrix.items(), key=lambda x: -len(x[1]))
    ]
    if demand_rows:
        df_demand = pd.DataFrame(demand_rows)
        fig = px.bar(
            df_demand,
            x="Interested Players",
            y="Game",
            orientation="h",
            color_discrete_sequence=[PRIMARY],
            template="plotly_dark",
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=max(300, len(demand_rows) * 32),
        )
        st.plotly_chart(fig, width="stretch")

    # 2. Demand Heatmap — Game × Time Slot (summed across locations)
    st.subheader("Demand Heatmap")

    slot_ids = list(slots)
    location_ids = list(locations)

    # Order games by total demand (highest first)
    game_demand_totals: dict[str, int] = {}
    for gid in games:
        game_demand_totals[gid] = sum(
            len(overlap_map.get((gid, sid, lid), set()))
            for sid in slot_ids
            for lid in location_ids
        )
    game_ids = sorted(games, key=lambda g: game_demand_totals.get(g, 0))

    # Build counts matrix
    raw_data: list[list[int]] = []
    for gid in game_ids:
        raw_data.append(
            [
                sum(
                    len(overlap_map.get((gid, sid, lid), set())) for lid in location_ids
                )
                for sid in slot_ids
            ]
        )

    if raw_data:
        display_data = [[float(v) for v in row] for row in raw_data]
        text_data = [[str(v) for v in row] for row in raw_data]

        fig_hm = go.Figure(
            data=go.Heatmap(
                z=display_data,
                x=slot_ids,
                y=game_ids,
                text=text_data,
                texttemplate="%{text}",
                textfont=dict(size=11),
                colorscale=[[0, SURFACE_RAISED], [0.5, ACCENT], [1, PRIMARY]],
                hovertemplate="Game: %{y}<br>Slot: %{x}<br>Eligible: %{z:.0f}<extra></extra>",
                colorbar=dict(title="Players"),
                xgap=2,
                ygap=2,
            )
        )
        fig_hm.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=max(350, len(game_ids) * 34),
            xaxis=dict(side="top"),
        )
        st.plotly_chart(fig_hm, width="stretch")

    # 3. Player Coverage
    st.subheader("Player Coverage")
    selected_sessions: list[CandidateSession] = st.session_state.get(
        "engine_selected", []
    )
    covered_players = {
        pid for s in selected_sessions if s.viable for pid in s.eligible_players
    }

    covered_count = len(covered_players)
    total_count = len(players)
    uncovered = sorted(players.keys() - covered_players)

    col1, col2 = st.columns(2)
    col1.metric("Covered", f"{covered_count} / {total_count}")
    col2.metric("Uncovered", f"{len(uncovered)}")
    if uncovered:
        with st.expander("Uncovered players"):
            st.write(", ".join(uncovered))

    # 5. Location Split — donut chart
    st.subheader("Location Demand Split")
    loc_counts: dict[str, int] = {}
    for player in players.values():
        for loc in player.location_prefs:
            loc_counts[loc] = loc_counts.get(loc, 0) + 1

    if loc_counts:
        fig_loc = px.pie(
            names=list(loc_counts.keys()),
            values=list(loc_counts.values()),
            hole=0.5,
            color_discrete_sequence=[PRIMARY, ACCENT, ALERT, SUCCESS],
            template="plotly_dark",
        )
        fig_loc.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=300,
        )
        st.plotly_chart(fig_loc, width="stretch")

    # 5. Unviable Games
    st.subheader("Unviable Games")
    if non_viable:
        # De-duplicate by (game, reason)
        seen: set[tuple[str, str]] = set()
        unique: list[CandidateSession] = []
        for c in non_viable:
            key = (c.game, c.rejection_reason or "")
            if key not in seen:
                seen.add(key)
                unique.append(c)

        reasons_df = pd.DataFrame(
            [
                {
                    "Game": c.game,
                    "Slot": c.slot,
                    "Location": c.location,
                    "Reason": c.rejection_reason,
                }
                for c in unique
            ]
        )
        st.dataframe(reasons_df, width="stretch", hide_index=True)
    else:
        st.success("All candidates are viable!")
