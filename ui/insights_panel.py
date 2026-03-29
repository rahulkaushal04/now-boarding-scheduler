"""Step 4 — Insights & Analytics.

All charts use ``plotly_dark`` template + brand colours.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from models.entities import CandidateSession, Game, Player
from ui.styles import PRIMARY, ACCENT, ALERT, SUCCESS, TEXT_SEC, SURFACE, SURFACE_RAISED


def render_insights(
    candidates: list[CandidateSession],
    players: dict[str, Player],
    games: dict[str, Game],
    demand_matrix: dict[str, set[str]],
    conflict_matrix: dict[tuple[str, str], int],
    slots: dict,
    locations: dict,
    overlap_map: dict,
) -> None:
    """Render the full analytics / insights dashboard."""
    st.header("Insights & Analytics")

    viable = [c for c in candidates if c.viable]
    non_viable = [c for c in candidates if not c.viable]

    # ------------------------------------------------------------------ #
    # 1. Game Demand Ranking — bar chart
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 2. Demand Heatmap — Game × Time Slot (summed across locations)
    # ------------------------------------------------------------------ #
    st.subheader("Demand Heatmap")

    # Preserve CSV column order for slots (chronological)
    slot_ids = list(slots.keys())

    # Order games by total demand (highest first)
    game_demand_totals: dict[str, int] = {}
    for gid in games:
        total = 0
        for sid in slot_ids:
            for lid in locations:
                total += len(overlap_map.get((gid, sid, lid), set()))
        game_demand_totals[gid] = total
    game_ids = sorted(games.keys(), key=lambda g: game_demand_totals.get(g, 0))

    # Build raw counts matrix
    raw_data: list[list[int]] = []
    for gid in game_ids:
        row: list[int] = []
        for sid in slot_ids:
            total = 0
            for lid in locations:
                total += len(overlap_map.get((gid, sid, lid), set()))
            row.append(total)
        raw_data.append(row)

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

    # ------------------------------------------------------------------ #
    # 3. Conflict Matrix
    # ------------------------------------------------------------------ #
    st.subheader("Conflict Matrix (Shared Players)")
    if conflict_matrix:
        all_game_ids = sorted({g for pair in conflict_matrix for g in pair})
        matrix: list[list[int]] = []
        for g1 in all_game_ids:
            row = [conflict_matrix.get((g1, g2), 0) for g2 in all_game_ids]
            matrix.append(row)

        fig_cm = go.Figure(
            data=go.Heatmap(
                z=matrix,
                x=all_game_ids,
                y=all_game_ids,
                colorscale=[[0, SURFACE_RAISED], [0.5, ACCENT], [1, ALERT]],
                hovertemplate="Game 1: %{y}<br>Game 2: %{x}<br>Shared: %{z}<extra></extra>",
            )
        )
        fig_cm.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=max(400, len(all_game_ids) * 30),
        )
        st.plotly_chart(fig_cm, width="stretch")

    # ------------------------------------------------------------------ #
    # 4. Player Coverage
    # ------------------------------------------------------------------ #
    st.subheader("Player Coverage")
    selected_sessions: list[CandidateSession] = st.session_state.get(
        "engine_selected", []
    )
    covered_players: set[str] = set()
    for s in selected_sessions:
        if s.viable:
            covered_players.update(s.eligible_players)

    covered_count = len(covered_players)
    total_count = len(players)
    uncovered = sorted(set(players.keys()) - covered_players)

    col1, col2 = st.columns(2)
    col1.metric("Covered", f"{covered_count} / {total_count}")
    col2.metric("Uncovered", f"{len(uncovered)}")
    if uncovered:
        with st.expander("Uncovered players"):
            st.write(", ".join(uncovered))

    # ------------------------------------------------------------------ #
    # 5. Location Split — donut chart
    # ------------------------------------------------------------------ #
    st.subheader("Location Demand Split")
    loc_counts: dict[str, int] = {}
    for pid, player in players.items():
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

    # ------------------------------------------------------------------ #
    # 6. Unviable Games
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 7. Time Slot Density — bar chart
    # ------------------------------------------------------------------ #
    st.subheader("Time Slot Density (Available Players)")
    slot_player_counts: dict[str, int] = {}
    for sid in slots:
        available = {pid for pid, p in players.items() if sid in p.time_availability}
        slot_player_counts[sid] = len(available)

    if slot_player_counts:
        # Preserve CSV column order (chronological)
        sdf = pd.DataFrame(
            [{"Slot": s, "Available Players": slot_player_counts[s]} for s in slots]
        )
        fig_slot = px.bar(
            sdf,
            x="Slot",
            y="Available Players",
            color_discrete_sequence=[PRIMARY],
            template="plotly_dark",
        )
        fig_slot.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=300,
        )
        st.plotly_chart(fig_slot, width="stretch")
