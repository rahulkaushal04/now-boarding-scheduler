"""Step 3 — Recommendations: timetable view of best sessions."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from models.entities import CandidateSession, Game, Slot
from ui.styles import (
    PRIMARY,
    ACCENT,
    ALERT,
    SURFACE,
    BORDER,
    TEXT_SEC,
    weight_badge_html,
)

_DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _day_sort_key(day: str) -> int:
    try:
        return _DAY_ORDER.index(day)
    except ValueError:
        return 99


def render_recommendations(
    candidates: list[CandidateSession],
    all_players: dict,
    games: dict[str, Game],
    all_candidates: list[CandidateSession] | None = None,
    slots: dict[str, Slot] | None = None,
) -> list[CandidateSession]:
    """Render the recommendation panel as a timetable.

    All viable selected sessions are shown in a day/time grid.
    Returns the viable sessions list.
    """
    slots = slots or {}

    viable = [c for c in candidates if c.viable]
    _all = all_candidates if all_candidates is not None else candidates
    non_viable = [c for c in _all if not c.viable]

    # ---- Hero-style header ----
    st.markdown(
        '<div class="hero-card">'
        '<div class="hero-title">Recommendations</div>'
        '<div class="hero-subtitle">'
        "Your best sessions for the week, based on player votes and availability."
        "</div></div>",
        unsafe_allow_html=True,
    )

    if not viable:
        st.markdown(
            '<div class="rec-empty">No recommendations right now.<br>'
            "Try changing the game rules or settings.</div>",
            unsafe_allow_html=True,
        )
        return []

    # ---- Stat counters ----
    st.markdown(
        '<div class="stat-row">'
        f'<div class="stat-item"><div class="stat-value">{len(viable)}</div>'
        f'<div class="stat-label">Sessions</div></div>'
        f'<div class="stat-item"><div class="stat-value">'
        f"{len({p for c in viable for p in c.eligible_players})}/{len(all_players)}</div>"
        f'<div class="stat-label">Players covered</div></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ---- Build timetable grid: rows = locations, cols = days ----
    day_set: set[str] = set()
    loc_set: set[str] = set()
    grid: dict[tuple[str, str], list[CandidateSession]] = defaultdict(list)

    for c in viable:
        slot_obj = slots.get(c.slot)
        day = slot_obj.day if slot_obj else c.slot
        day_set.add(day)
        loc_set.add(c.location)
        grid[(day, c.location)].append(c)

    sorted_days = sorted(day_set, key=_day_sort_key)
    sorted_locs = sorted(loc_set)

    # ---- Render timetable ----
    # Header row
    header_cols = st.columns([1] + [2] * len(sorted_days))
    with header_cols[0]:
        st.markdown(
            f'<div style="padding:0.5rem 0;color:{TEXT_SEC};'
            f'font-weight:600;font-size:0.85em">Place</div>',
            unsafe_allow_html=True,
        )
    for i, day in enumerate(sorted_days):
        with header_cols[i + 1]:
            st.markdown(
                f'<div style="padding:0.5rem 0;color:{PRIMARY};'
                f'font-weight:700;font-size:0.92em;text-align:center">{day}</div>',
                unsafe_allow_html=True,
            )

    # Data rows
    for loc in sorted_locs:
        row_cols = st.columns([1] + [2] * len(sorted_days))
        with row_cols[0]:
            st.markdown(
                f'<div style="padding:0.6rem 0;color:{TEXT_SEC};'
                f'font-size:0.88em;font-weight:500">{loc}</div>',
                unsafe_allow_html=True,
            )
        for i, day in enumerate(sorted_days):
            with row_cols[i + 1]:
                sessions = grid.get((day, loc), [])
                if sessions:
                    for c in sessions:
                        wc = games.get(c.game)
                        wclass = wc.weight_class if wc else "medium"
                        border_color = PRIMARY if wclass == "heavy" else ACCENT
                        slot_obj = slots.get(c.slot)
                        time_label = slot_obj.time if slot_obj else c.slot
                        st.markdown(
                            f'<div class="rec-card" style="border-left:4px solid '
                            f'{border_color};padding:0.6rem 0.8rem;margin-bottom:0.35rem">'
                            f'<strong style="font-size:0.92em">{c.game}</strong> '
                            f"{weight_badge_html(wclass)}<br>"
                            f'<span style="color:{TEXT_SEC};font-size:0.82em">'
                            f"{time_label} / {c.eligible_count} players</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        f'<div style="padding:0.6rem;text-align:center;'
                        f'color:{BORDER};font-size:0.85em">—</div>',
                        unsafe_allow_html=True,
                    )

    # ---- Non-viable section ----
    if non_viable:
        seen: set[tuple[str, str]] = set()
        unique_non_viable: list[CandidateSession] = []
        for c in non_viable:
            key = (c.game, c.rejection_reason or "")
            if key not in seen:
                seen.add(key)
                unique_non_viable.append(c)

        with st.expander(
            f"Can't be scheduled ({len(unique_non_viable)})", expanded=False
        ):
            for c in unique_non_viable:
                st.markdown(
                    f'<div class="nv-item">'
                    f"<strong>{c.game}</strong> / {c.slot} / {c.location}<br>"
                    f'<span class="nv-reason">{c.rejection_reason}</span></div>',
                    unsafe_allow_html=True,
                )

    return viable
