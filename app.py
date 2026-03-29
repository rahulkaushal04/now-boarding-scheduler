"""Now Boarding Scheduler — Streamlit entry point.

Four-step wizard: Upload → Game Rules → Recommendations → Insights.

Manages session state, orchestrates entity construction from uploaded
CSV data, and drives the scoring / selection / explanation engine.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

# Page config must be the first Streamlit call
st.set_page_config(
    page_title="Now Boarding Scheduler",
    page_icon="\U0001f3b2",
    layout="wide",
)

from data.processor import (
    build_slots,
    build_games,
    build_players,
    build_locations,
    build_overlap_map,
    build_demand_matrix,
    build_conflict_matrix,
)
from engine.selector import select_sessions
from ui.insights_panel import render_insights
from engine.scorer import score_all_candidates
from models.config_model import SchedulerConfig
from ui.game_rules_panel import render_game_rules
from ui.styles import TEXT_SEC, inject_custom_css
from ui.upload_panel import render_upload_section
from ui.recommend_panel import render_recommendations
from engine.explainer import add_conflict_notes, explain_candidate

inject_custom_css()

if "step" not in st.session_state:
    st.session_state["step"] = 1

_STEP_LABELS: dict[int, str] = {
    1: "Upload",
    2: "Game Rules",
    3: "Recommendations",
    4: "Insights",
}

_REQUIRED_UPLOAD_KEYS = (
    "upload_heavy_df",
    "upload_medium_df",
    "upload_timings_df",
    "upload_place_df",
)

_ENGINE_CACHE_KEYS = (
    "engine_candidates",
    "engine_selected",
    "engine_demand_matrix",
    "engine_conflict_matrix",
    "engine_overlap_map",
)


def _step_indicator() -> None:
    """Render a horizontal step-progress bar with numbered pills."""
    current: int = st.session_state["step"]
    pills: list[str] = []
    for i, label in _STEP_LABELS.items():
        if i < current:
            cls, num = "step-pill done", "\u2714"
        elif i == current:
            cls, num = "step-pill active", str(i)
        else:
            cls, num = "step-pill pending", str(i)
        pills.append(
            f'<div class="{cls}">' f'<span class="step-num">{num}</span>{label}</div>'
        )
    st.markdown(
        '<div class="step-bar">' + "".join(pills) + "</div>",
        unsafe_allow_html=True,
    )


def _clear_engine_cache() -> None:
    """Evict cached engine results so they are recomputed on next run."""
    for key in _ENGINE_CACHE_KEYS:
        st.session_state.pop(key, None)


def _has_required_uploads() -> bool:
    """Return *True* when all four upload DataFrames are present and non-empty."""
    return all(
        isinstance(df := st.session_state.get(key), pd.DataFrame) and not df.empty
        for key in _REQUIRED_UPLOAD_KEYS
    )


def _get_state(key: str, default: Any = None) -> Any:
    """Shorthand for ``st.session_state.get``."""
    return st.session_state.get(key, default)


def _build_entities() -> None:
    """Build Player, Game, Slot, Location objects from uploaded DataFrames."""
    heavy_df: pd.DataFrame = st.session_state["upload_heavy_df"]
    medium_df: pd.DataFrame = st.session_state["upload_medium_df"]
    timings_df: pd.DataFrame = st.session_state["upload_timings_df"]
    place_df: pd.DataFrame = st.session_state["upload_place_df"]

    players = build_players(heavy_df, medium_df, timings_df, place_df)
    st.session_state["entity_players"] = players
    st.session_state["entity_games"] = build_games(heavy_df, medium_df, players)
    st.session_state["entity_slots"] = build_slots(timings_df)
    st.session_state["entity_locations"] = build_locations(place_df)


def _run_engine() -> None:
    """Execute the scoring → selection → explanation pipeline and cache results."""
    players = st.session_state["entity_players"]
    games = _get_state("rules_games", st.session_state["entity_games"])
    slots = st.session_state["entity_slots"]
    locations = st.session_state["entity_locations"]
    config: SchedulerConfig = _get_state("scheduler_config", SchedulerConfig())

    overlap_map = build_overlap_map(players, games, slots, locations)
    demand_matrix = build_demand_matrix(players)
    conflict_matrix = build_conflict_matrix(demand_matrix)
    all_player_ids = set(players)

    with st.spinner("Crunching the numbers..."):
        candidates = score_all_candidates(
            overlap_map, games, demand_matrix, slots, locations, all_player_ids
        )
        selected = select_sessions(candidates, config, conflict_matrix, all_player_ids)

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

step: int = st.session_state["step"]

if step == 1:
    _files, config = render_upload_section()
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

elif step == 2:
    players = _get_state("entity_players", {})
    original_games = _get_state("entity_games", {})
    games = _get_state("rules_games", original_games)
    slots = _get_state("entity_slots", {})
    locations = _get_state("entity_locations", {})

    st.session_state["rules_games"] = render_game_rules(
        games, players, slots, locations, original_games
    )

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

elif step == 3:
    if "engine_candidates" not in st.session_state:
        _run_engine()

    render_recommendations(
        st.session_state["engine_selected"],
        st.session_state["entity_players"],
        _get_state("rules_games", st.session_state["entity_games"]),
        st.session_state["engine_candidates"],
        st.session_state["entity_slots"],
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

elif step == 4:
    if "engine_candidates" not in st.session_state:
        _run_engine()

    render_insights(
        candidates=st.session_state["engine_candidates"],
        players=st.session_state["entity_players"],
        games=_get_state("rules_games", st.session_state["entity_games"]),
        demand_matrix=st.session_state["engine_demand_matrix"],
        conflict_matrix=st.session_state["engine_conflict_matrix"],
        slots=st.session_state["entity_slots"],
        locations=st.session_state["entity_locations"],
        overlap_map=st.session_state["engine_overlap_map"],
    )

    if st.button("\u2190 Back to Recommendations"):
        st.session_state["step"] = 3
        st.rerun()
