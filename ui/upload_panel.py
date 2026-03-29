"""Step 1 — File upload + session configuration."""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from data.loader import (
    load_game_csv,
    load_timings_csv,
    load_place_csv,
    load_metadata_csv,
)
from data.validators import validate_cross_files
from models.config_model import SchedulerConfig
from ui.styles import PRIMARY, SUCCESS, ALERT, TEXT_SEC


def render_upload_section() -> tuple[dict[str, Any], SchedulerConfig]:
    """Render the upload panel (file uploaders + config inputs).

    Returns ``(files_dict, scheduler_config)``.
    """
    st.header("Upload Poll CSVs")

    col_left, col_right = st.columns([2, 1])

    # ----- File uploaders -----
    with col_left:
        heavy_file = st.file_uploader(
            "Heavy Games CSV", type=["csv"], key="upload_heavy"
        )
        medium_file = st.file_uploader(
            "Medium Games CSV", type=["csv"], key="upload_medium"
        )
        timings_file = st.file_uploader(
            "Timings CSV", type=["csv"], key="upload_timings"
        )
        place_file = st.file_uploader(
            "Place / Location CSV", type=["csv"], key="upload_place"
        )
        metadata_file = st.file_uploader(
            "Game Metadata CSV", type=["csv"], key="upload_metadata"
        )

    # ----- Config inputs -----
    with col_right:
        st.subheader("Session Config")
        target = st.number_input(
            "Target sessions per week",
            min_value=1,
            max_value=10,
            value=4,
            key="config_target_sessions",
            help="How many game sessions to schedule this week.",
        )
        max_tables = st.number_input(
            "Max tables per slot per location",
            min_value=1,
            max_value=3,
            value=1,
            key="config_max_tables",
            help="Maximum simultaneous tables at one location in one time slot.",
        )
        max_repeats = st.number_input(
            "Max repeats of a game per week",
            min_value=1,
            max_value=3,
            value=1,
            key="config_max_repeats",
            help="How many times the same game may be scheduled in one week.",
        )

    config = SchedulerConfig(
        target_sessions=int(target),
        max_tables_per_slot=int(max_tables),
        max_repeats_per_week=int(max_repeats),
    )

    files: dict[str, Any] = {
        "heavy": heavy_file,
        "medium": medium_file,
        "timings": timings_file,
        "place": place_file,
        "metadata": metadata_file,
    }

    # ----- Parse & validate -----
    all_errors: list[str] = []
    all_warnings: list[str] = []

    heavy_df = pd.DataFrame()
    medium_df = pd.DataFrame()
    timings_df = pd.DataFrame()
    place_df = pd.DataFrame()
    metadata_df = pd.DataFrame()

    if heavy_file is not None:
        heavy_file.seek(0)
        heavy_df, errs = load_game_csv(heavy_file, "heavy")
        all_errors.extend(errs)
    if medium_file is not None:
        medium_file.seek(0)
        medium_df, errs = load_game_csv(medium_file, "medium")
        all_errors.extend(errs)
    if timings_file is not None:
        timings_file.seek(0)
        timings_df, errs = load_timings_csv(timings_file)
        all_errors.extend(errs)
    if place_file is not None:
        place_file.seek(0)
        place_df, errs = load_place_csv(place_file)
        all_errors.extend(errs)
    if metadata_file is not None:
        metadata_file.seek(0)
        metadata_df, errs = load_metadata_csv(metadata_file)
        all_errors.extend(errs)

    # Cross-file validation (only when we have at least some files)
    uploaded_count = sum(1 for f in files.values() if f is not None)
    if uploaded_count >= 2:
        all_warnings = validate_cross_files(
            heavy_df, medium_df, timings_df, place_df, metadata_df
        )

    # ----- Feedback -----
    if all_errors:
        for err in all_errors:
            st.error(err)
    if all_warnings:
        with st.expander(f"\u26a0\ufe0f {len(all_warnings)} warning(s)", expanded=False):
            for w in all_warnings:
                st.warning(w)

    # ----- Data preview -----
    if uploaded_count > 0:
        # Collect summary stats
        game_players: set[str] = set()
        all_games: set[str] = set()
        all_slots: set[str] = set()
        all_locations: set[str] = set()

        from config import EXCLUDED_COLUMNS
        from utils.names import extract_courtesy_owner

        if not heavy_df.empty:
            game_players.update(heavy_df["Name"].tolist())
            for c in heavy_df.columns:
                if c not in EXCLUDED_COLUMNS:
                    base, _ = extract_courtesy_owner(c)
                    all_games.add(base)
        if not medium_df.empty:
            game_players.update(medium_df["Name"].tolist())
            for c in medium_df.columns:
                if c not in EXCLUDED_COLUMNS:
                    base, _ = extract_courtesy_owner(c)
                    all_games.add(base)
        if not timings_df.empty:
            all_slots.update(
                c for c in timings_df.columns if c not in EXCLUDED_COLUMNS
            )
        if not place_df.empty:
            all_locations.update(
                c for c in place_df.columns if c not in EXCLUDED_COLUMNS
            )

        st.markdown(
            f'<div class="summary-card">'
            f"<strong style='color:{PRIMARY}'>Summary</strong><br>"
            f"<span style='color:{TEXT_SEC}'>"
            f"Found <strong>{len(game_players)}</strong> players · "
            f"<strong>{len(all_games)}</strong> games · "
            f"<strong>{len(all_slots)}</strong> time slots · "
            f"<strong>{len(all_locations)}</strong> locations"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        with st.expander("Data preview"):
            if not heavy_df.empty:
                st.caption("Heavy Games")
                st.dataframe(heavy_df, use_container_width=True, hide_index=True)
            if not medium_df.empty:
                st.caption("Medium Games")
                st.dataframe(medium_df, use_container_width=True, hide_index=True)
            if not timings_df.empty:
                st.caption("Timings")
                st.dataframe(timings_df, use_container_width=True, hide_index=True)
            if not place_df.empty:
                st.caption("Locations")
                st.dataframe(place_df, use_container_width=True, hide_index=True)

    # Store parsed frames for later steps
    st.session_state["upload_heavy_df"] = heavy_df
    st.session_state["upload_medium_df"] = medium_df
    st.session_state["upload_timings_df"] = timings_df
    st.session_state["upload_place_df"] = place_df
    st.session_state["upload_metadata_df"] = metadata_df

    return files, config
