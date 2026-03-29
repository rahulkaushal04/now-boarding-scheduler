"""Now Boarding Scheduler - Streamlit entry point.

4-step wizard:  Upload → Game Rules → Recommendations → Insights

Manages session state and orchestrates the data / engine pipeline.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Now Boarding Scheduler",
    page_icon="\U0001f3b2",
    layout="wide",
)

from ui.styles import inject_custom_css, PRIMARY, TEXT_SEC, TEXT_MUTED
from ui.upload_panel import render_upload_section
from ui.game_rules_panel import render_game_rules
from ui.recommend_panel import render_recommendations
from ui.insights_panel import render_insights
from data.processor import (
    build_players,
    build_games,
    build_slots,
    build_locations,
    build_overlap_map,
    build_demand_matrix,
    build_conflict_matrix,
)
from engine.scorer import score_all_candidates
from engine.selector import select_sessions
from engine.explainer import explain_candidate, add_conflict_notes
from models.config_model import SchedulerConfig

import pandas as pd

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
inject_custom_css()

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
if "step" not in st.session_state:
    st.session_state["step"] = 1

STEP_LABELS = {1: "Upload", 2: "Game Rules", 3: "Recommendations", 4: "Insights"}


def _step_indicator() -> None:
    """Render a horizontal step indicator with numbered pills."""
    current = st.session_state["step"]
    pills: list[str] = []
    for i, label in STEP_LABELS.items():
        if i < current:
            cls = "step-pill done"
            num_content = "\u2714"
        elif i == current:
            cls = "step-pill active"
            num_content = str(i)
        else:
            cls = "step-pill pending"
            num_content = str(i)
        pills.append(
            f'<div class="{cls}">'
            f'<span class="step-num">{num_content}</span>{label}</div>'
        )
    st.markdown(
        '<div class="step-bar">' + "".join(pills) + "</div>",
        unsafe_allow_html=True,
    )


def _clear_engine_cache() -> None:
    """Remove cached engine results so they are recomputed."""
    for key in [
        "engine_candidates",
        "engine_selected",
        "engine_demand_matrix",
        "engine_conflict_matrix",
        "engine_overlap_map",
    ]:
        st.session_state.pop(key, None)


def _has_required_uploads() -> bool:
    for key in [
        "upload_heavy_df",
        "upload_medium_df",
        "upload_timings_df",
        "upload_place_df",
    ]:
        df = st.session_state.get(key)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return False
    return True


def _build_entities():
    """Build players, games, slots, locations from parsed DataFrames and cache."""
    heavy_df = st.session_state["upload_heavy_df"]
    medium_df = st.session_state["upload_medium_df"]
    timings_df = st.session_state["upload_timings_df"]
    place_df = st.session_state["upload_place_df"]
    players = build_players(heavy_df, medium_df, timings_df, place_df)
    games = build_games(heavy_df, medium_df, players)
    slots = build_slots(timings_df)
    locations = build_locations(place_df)

    st.session_state["entity_players"] = players
    st.session_state["entity_games"] = games
    st.session_state["entity_slots"] = slots
    st.session_state["entity_locations"] = locations


def _run_engine() -> None:
    """Execute the full scoring → selection → explanation pipeline.  Cached."""
    players = st.session_state["entity_players"]
    games = st.session_state.get("rules_games", st.session_state["entity_games"])
    slots = st.session_state["entity_slots"]
    locations = st.session_state["entity_locations"]
    config = st.session_state.get(
        "scheduler_config",
        SchedulerConfig(),
    )

    overlap_map = build_overlap_map(players, games, slots, locations)
    demand_matrix = build_demand_matrix(players)
    conflict_matrix = build_conflict_matrix(demand_matrix)
    all_player_ids = set(players.keys())

    with st.spinner("Crunching the numbers..."):
        candidates = score_all_candidates(
            overlap_map, games, demand_matrix, slots, locations, all_player_ids
        )
        selected = select_sessions(candidates, config, conflict_matrix, all_player_ids)

        # Generate reasoning for selected sessions
        covered: set[str] = set()
        for rank, sess in enumerate(selected, 1):
            sess.reasoning = explain_candidate(
                sess, demand_matrix, all_player_ids, covered, games, rank
            )
            covered.update(sess.eligible_players)

        add_conflict_notes(selected, conflict_matrix)

    st.session_state["engine_candidates"] = candidates
    st.session_state["engine_selected"] = selected
    st.session_state["engine_demand_matrix"] = demand_matrix
    st.session_state["engine_conflict_matrix"] = conflict_matrix
    st.session_state["engine_overlap_map"] = overlap_map


# ---------------------------------------------------------------------------
# Main app flow
# ---------------------------------------------------------------------------
st.title("Now Boarding Scheduler")
_step_indicator()

step = st.session_state["step"]

# ============================  STEP 1  ==================================
if step == 1:
    files, config = render_upload_section()
    st.session_state["scheduler_config"] = config

    if _has_required_uploads():
        if st.button("Next \u2192 Game Rules", type="primary"):
            _build_entities()
            _clear_engine_cache()
            st.session_state["step"] = 2
            st.rerun()
    else:
        st.markdown(
            '<div class="summary-card" style="text-align:center;padding:2rem">'
            f'<span style="color:{TEXT_SEC};font-size:1.05em">'
            "Please add all four files to continue</span></div>",
            unsafe_allow_html=True,
        )

# ============================  STEP 2  ==================================
elif step == 2:
    players = st.session_state.get("entity_players", {})
    original_games = st.session_state.get("entity_games", {})
    games = st.session_state.get("rules_games", original_games)
    slots = st.session_state.get("entity_slots", {})
    locations = st.session_state.get("entity_locations", {})

    updated_games = render_game_rules(games, players, slots, locations, original_games)
    st.session_state["rules_games"] = updated_games

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("\u2190 Back to Upload"):
            st.session_state["step"] = 1
            st.rerun()
    with col_next:
        if st.button("Next \u2192 Recommendations", type="primary"):
            _clear_engine_cache()
            _run_engine()
            st.session_state["step"] = 3
            st.rerun()

# ============================  STEP 3  ==================================
elif step == 3:
    # Ensure engine has run
    if "engine_candidates" not in st.session_state:
        _run_engine()

    candidates = st.session_state["engine_candidates"]
    selected = st.session_state["engine_selected"]
    players = st.session_state["entity_players"]
    games = st.session_state.get("rules_games", st.session_state["entity_games"])

    accepted = render_recommendations(
        selected, players, games, candidates, st.session_state["entity_slots"]
    )

    st.divider()

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("\u2190 Back to Game Rules"):
            _clear_engine_cache()
            st.session_state["step"] = 2
            st.rerun()
    with col_next:
        if st.button("Next \u2192 Insights", type="primary"):
            st.session_state["step"] = 4
            st.rerun()

# ============================  STEP 4  ==================================
elif step == 4:
    if "engine_candidates" not in st.session_state:
        _run_engine()

    render_insights(
        candidates=st.session_state["engine_candidates"],
        players=st.session_state["entity_players"],
        games=st.session_state.get("rules_games", st.session_state["entity_games"]),
        demand_matrix=st.session_state["engine_demand_matrix"],
        conflict_matrix=st.session_state["engine_conflict_matrix"],
        slots=st.session_state["entity_slots"],
        locations=st.session_state["entity_locations"],
        overlap_map=st.session_state["engine_overlap_map"],
    )

    if st.button("\u2190 Back to Recommendations"):
        st.session_state["step"] = 3
        st.rerun()
