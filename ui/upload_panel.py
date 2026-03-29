"""Step 1 - File upload and session configuration."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from data.loader import (
    load_game_csv,
    load_timings_csv,
    load_place_csv,
)
from data.validators import validate_cross_files
from models.config_model import SchedulerConfig
from ui.styles import PRIMARY, SUCCESS, ACCENT, TEXT_MUTED


# ---------------------------------------------------------------------------
# Data source descriptors
# ---------------------------------------------------------------------------
_DATA_SOURCES = [
    {
        "key": "heavy",
        "label": "Heavy Games",
        "desc": "Poll results for complex or long games",
    },
    {
        "key": "medium",
        "label": "Medium Games",
        "desc": "Poll results for lighter or shorter games",
    },
    {
        "key": "timings",
        "label": "Timings",
        "desc": "When each player is available to play",
    },
    {"key": "place", "label": "Locations", "desc": "Where each player prefers to play"},
]


def _parse_pasted_csv(text: str) -> io.StringIO | None:
    """Return a StringIO if text looks like CSV, else None."""
    stripped = text.strip()
    if not stripped:
        return None
    return io.StringIO(stripped)


def _input_widget(key: str, label: str, desc: str) -> tuple[Any, str | None]:
    """Render a compact input that supports file upload OR paste.

    Returns (file_obj_or_None, pasted_text_or_None).
    """
    mode = st.radio(
        "Input method",
        ["Upload file", "Paste CSV"],
        key=f"mode_{key}",
        horizontal=True,
        label_visibility="collapsed",
    )

    file_obj = None
    pasted = None

    if mode == "Upload file":
        file_obj = st.file_uploader(
            label,
            type=["csv"],
            key=f"upload_{key}",
            label_visibility="collapsed",
        )
    else:
        pasted = st.text_area(
            f"Paste {label} CSV content",
            key=f"paste_{key}",
            height=150,
            placeholder=f"Paste your {label} CSV here\u2026",
            label_visibility="collapsed",
        )
        st.button("Submit", key=f"submit_{key}", type="secondary")

    return file_obj, pasted


def render_upload_section() -> tuple[dict[str, Any], SchedulerConfig]:
    """Render the upload panel.

    Returns ``(files_dict, scheduler_config)``.
    """
    # ---- Intro ----

    # Clear cached data when "Use example data" is unchecked
    # Must happen before columns render so tab indicators see the cleared state
    _use_example_now = st.session_state.get("use_example_data", False)
    if not _use_example_now and st.session_state.get("_prev_use_example", False):
        for _src in _DATA_SOURCES:
            st.session_state.pop(f"upload_{_src['key']}_df", None)
    st.session_state["_prev_use_example"] = _use_example_now

    st.markdown(
        '<div class="hero-card">'
        '<div class="hero-title">Now Boarding Scheduler</div>'
        '<div class="hero-subtitle">'
        "Add your poll data and set up the session. "
        "You can upload CSV files or paste the data directly."
        "</div></div>",
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 2], gap="large")

    # ----- Data inputs (tabs) -----
    sources: dict[str, tuple[Any, str | None]] = {}

    with col_left:
        tabs = st.tabs([s["label"] for s in _DATA_SOURCES])
        for tab, source in zip(tabs, _DATA_SOURCES):
            with tab:
                st.caption(source["desc"])
                sources[source["key"]] = _input_widget(
                    source["key"], source["label"], source["desc"]
                )
                # Show indicator when previously loaded data is available
                _cached_key = f"upload_{source['key']}_df"
                _cached = st.session_state.get(_cached_key)
                f_obj, p_txt = sources[source["key"]]
                if (
                    _cached is not None
                    and isinstance(_cached, pd.DataFrame)
                    and not _cached.empty
                    and f_obj is None
                    and not (p_txt and p_txt.strip())
                ):
                    st.success(
                        f"Previously loaded data available ({len(_cached)} rows)"
                    )

    # ----- Config inputs -----
    with col_right:
        st.markdown(
            '<div class="config-card">'
            '<div class="config-title">Session Config</div></div>',
            unsafe_allow_html=True,
        )
        max_repeats = st.number_input(
            "Max times a game can be scheduled per week",
            min_value=1,
            max_value=3,
            value=1,
            key="config_max_repeats",
            help="How many times the same game can appear in one week.",
        )

        use_example = st.checkbox(
            "Use example data",
            key="use_example_data",
            help="Load pre-filled example data so you can try the app right away.",
        )

        if use_example:
            st.caption(
                "Example data is now loaded. You can preview it below "
                "or download the CSV files to see the exact format."
            )

        # Download sample data as zip
        _EXAMPLE_DIR_DL = Path(__file__).resolve().parent.parent / "example_data"
        _SAMPLE_FILES = [
            ("heavy_games.csv", _EXAMPLE_DIR_DL / "heavy_games.csv"),
            ("medium_games.csv", _EXAMPLE_DIR_DL / "medium_games.csv"),
            ("timings.csv", _EXAMPLE_DIR_DL / "timings.csv"),
            ("place.csv", _EXAMPLE_DIR_DL / "place.csv"),
        ]
        if all(p.exists() for _, p in _SAMPLE_FILES):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, path in _SAMPLE_FILES:
                    zf.writestr(name, path.read_text(encoding="utf-8"))
            buf.seek(0)
            st.download_button(
                "Download sample CSVs",
                data=buf,
                file_name="sample_data.zip",
                mime="application/zip",
                use_container_width=True,
            )

        # Upload progress
        provided_count = 0
        for src in _DATA_SOURCES:
            _k = src["key"]
            _f, _p = sources[_k]
            if _f is not None or (_p and _p.strip()):
                provided_count += 1
            else:
                _ck = f"upload_{_k}_df"
                _cv = st.session_state.get(_ck)
                if _cv is not None and isinstance(_cv, pd.DataFrame) and not _cv.empty:
                    provided_count += 1
        progress_color = (
            SUCCESS
            if provided_count == 4
            else ACCENT if provided_count > 0 else TEXT_MUTED
        )
        st.markdown(
            f'<div style="margin-top:1.5rem;padding:0.75rem 1rem;background:#1B1F27;'
            f'border:1px solid #2D333B;border-radius:10px;text-align:center">'
            f'<span style="color:{progress_color};font-weight:700;font-size:1.3em">'
            f"{provided_count}/4</span>"
            f'<br><span style="color:#6B7280;font-size:0.82em">files added</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    config = SchedulerConfig(
        max_repeats_per_week=int(max_repeats),
    )

    # ----- Parse & validate -----
    all_errors: list[str] = []

    _EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "example_data"
    _EXAMPLE_FILES = {
        "heavy": _EXAMPLE_DIR / "heavy_games.csv",
        "medium": _EXAMPLE_DIR / "medium_games.csv",
        "timings": _EXAMPLE_DIR / "timings.csv",
        "place": _EXAMPLE_DIR / "place.csv",
    }

    def _resolve(key: str, loader, *loader_args):
        """Parse from file, pasted text, example data, or cached session data."""
        file_obj, pasted = sources[key]
        if file_obj is not None:
            file_obj.seek(0)
            return loader(file_obj, *loader_args)
        if pasted and pasted.strip():
            sio = _parse_pasted_csv(pasted)
            if sio:
                return loader(sio, *loader_args)
        if use_example and _EXAMPLE_FILES[key].exists():
            return loader(str(_EXAMPLE_FILES[key]), *loader_args)
        # Fall back to previously parsed data in session state
        session_key = f"upload_{key}_df"
        cached = st.session_state.get(session_key)
        if cached is not None and isinstance(cached, pd.DataFrame) and not cached.empty:
            return cached, []
        return pd.DataFrame(), []

    heavy_df, errs = _resolve("heavy", load_game_csv, "heavy")
    all_errors.extend(errs)
    medium_df, errs = _resolve("medium", load_game_csv, "medium")
    all_errors.extend(errs)
    timings_df, errs = _resolve("timings", load_timings_csv)
    all_errors.extend(errs)
    place_df, errs = _resolve("place", load_place_csv)
    all_errors.extend(errs)

    # Cross-file validation (only when all four are provided)
    uploaded_count = sum(
        1 for df in (heavy_df, medium_df, timings_df, place_df) if not df.empty
    )
    all_warnings: list[str] = []
    if uploaded_count == 4:
        all_warnings = validate_cross_files(heavy_df, medium_df, timings_df, place_df)

    # ----- Feedback -----
    if all_errors:
        for err in all_errors:
            st.error(err)
    if all_warnings:
        with st.expander(f"{len(all_warnings)} warning(s)", expanded=False):
            for w in all_warnings:
                st.warning(w)

    # ----- Stat counters -----
    if uploaded_count > 0:
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
            all_slots.update(c for c in timings_df.columns if c not in EXCLUDED_COLUMNS)
        if not place_df.empty:
            all_locations.update(
                c for c in place_df.columns if c not in EXCLUDED_COLUMNS
            )

        st.markdown(
            '<div class="stat-row">'
            f'<div class="stat-item">'
            f'<div class="stat-value">{len(game_players)}</div>'
            f'<div class="stat-label">Players</div></div>'
            f'<div class="stat-item">'
            f'<div class="stat-value">{len(all_games)}</div>'
            f'<div class="stat-label">Games</div></div>'
            f'<div class="stat-item">'
            f'<div class="stat-value">{len(all_slots)}</div>'
            f'<div class="stat-label">Time Slots</div></div>'
            f'<div class="stat-item">'
            f'<div class="stat-value">{len(all_locations)}</div>'
            f'<div class="stat-label">Locations</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        with st.expander("Preview uploaded data"):
            if not heavy_df.empty:
                st.caption("Heavy Games")
                st.dataframe(heavy_df, width="stretch", hide_index=True)
            if not medium_df.empty:
                st.caption("Medium Games")
                st.dataframe(medium_df, width="stretch", hide_index=True)
            if not timings_df.empty:
                st.caption("Timings")
                st.dataframe(timings_df, width="stretch", hide_index=True)
            if not place_df.empty:
                st.caption("Locations")
                st.dataframe(place_df, width="stretch", hide_index=True)

    # Store parsed frames
    st.session_state["upload_heavy_df"] = heavy_df
    st.session_state["upload_medium_df"] = medium_df
    st.session_state["upload_timings_df"] = timings_df
    st.session_state["upload_place_df"] = place_df

    files: dict[str, Any] = {
        "heavy": sources["heavy"][0],
        "medium": sources["medium"][0],
        "timings": sources["timings"][0],
        "place": sources["place"][0],
    }
    return files, config
