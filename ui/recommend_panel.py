"""Step 3 — Recommendations: timetable view of best sessions.

Renders a day × location grid of the highest-scoring viable sessions
selected by the engine, plus a collapsible section for non-viable
candidates and their rejection reasons.
"""

from collections import defaultdict

import streamlit as st

from models.entities import CandidateSession, Game, Player, Slot
from ui.styles import (
    ACCENT,
    BORDER,
    PRIMARY,
    TEXT,
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
    """Return a calendar sort index for a weekday name.

    Args:
        day (str): Weekday name (e.g. ``"Monday"``).

    Returns:
        int: Index 0–6 (Monday–Sunday), or 99 for unrecognised values.

    Example:
        >>> _day_sort_key("Monday")
        0
        >>> _day_sort_key("Sunday")
        6
    """
    try:
        return _DAY_ORDER.index(day)
    except ValueError:
        return 99


def render_recommendations(
    candidates: list[CandidateSession],
    all_players: dict[str, Player],
    games: dict[str, Game],
    all_candidates: list[CandidateSession] | None = None,
    slots: dict[str, Slot] | None = None,
    suggestions: list[CandidateSession] | None = None,
) -> list[CandidateSession]:
    """Render the recommendation panel as a day × location timetable.

    Args:
        candidates: Selected (viable) sessions from the engine.
        all_players: Full player dict for coverage stats.
        games: Game objects keyed by id.
        all_candidates: Complete candidate list (viable + non-viable).
        slots: Slot objects for day/time resolution.
        suggestions: Near-miss candidates that almost made the schedule.

    Returns:
        List of viable sessions shown in the timetable.
    """
    slots = slots or {}
    suggestions = suggestions or []

    viable = [c for c in candidates if c.viable]
    pool = all_candidates if all_candidates is not None else candidates
    non_viable = [c for c in pool if not c.viable]

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
    covered_players = {p for c in viable for p in c.eligible_players}
    st.markdown(
        '<div class="stat-row">'
        f'<div class="stat-item"><div class="stat-value">{len(viable)}</div>'
        f'<div class="stat-label">Sessions</div></div>'
        f'<div class="stat-item"><div class="stat-value">'
        f"{len(covered_players)}/{len(all_players)}</div>"
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
        grid[day, c.location].append(c)

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
                if not sessions:
                    st.markdown(
                        f'<div style="padding:0.6rem;text-align:center;'
                        f'color:{BORDER};font-size:0.85em">—</div>',
                        unsafe_allow_html=True,
                    )
                    continue
                for c in sessions:
                    wc = games.get(c.game)
                    wclass = wc.weight_class if wc else "medium"
                    border_color = PRIMARY if wclass == "heavy" else ACCENT
                    slot_obj = slots.get(c.slot)
                    time_label = slot_obj.time if slot_obj else c.slot
                    overflow_badge = (
                        ' <span style="background:#f59e0b;color:#fff;'
                        "padding:1px 6px;border-radius:8px;font-size:0.7em;"
                        'margin-left:4px">2nd table</span>'
                        if c.is_overflow
                        else ""
                    )
                    st.markdown(
                        f'<div class="rec-card" style="border-left:4px solid '
                        f'{border_color};padding:0.6rem 0.8rem;margin-bottom:0.35rem">'
                        f'<strong style="font-size:0.92em">{c.game}</strong> '
                        f"{weight_badge_html(wclass)}{overflow_badge}<br>"
                        f'<span style="color:{TEXT_SEC};font-size:0.82em">'
                        f"{time_label} / {c.eligible_count} players</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # ---- Suggestions: high-demand games that almost made it ----
    if suggestions:
        # Group suggestions by game, keep only the best option per game
        best_per_game: dict[str, CandidateSession] = {}
        for c in suggestions:
            prev = best_per_game.get(c.game)
            if prev is None or c.viability_score > prev.viability_score:
                best_per_game[c.game] = c

        unique_suggestions = sorted(
            best_per_game.values(),
            key=lambda c: c.viability_score,
            reverse=True,
        )

        with st.expander(
            f"Almost made it ({len(unique_suggestions)} games)", expanded=False
        ):
            # Render in a compact two-column grid
            cols = st.columns(2)
            for i, c in enumerate(unique_suggestions):
                wc = games.get(c.game)
                wclass = wc.weight_class if wc else "medium"
                slot_obj = slots.get(c.slot)
                time_label = slot_obj.time if slot_obj else c.slot
                day_label = slot_obj.day if slot_obj else ""
                reason = c.suggestion_reason or "Could not fit in the schedule"
                border_color = PRIMARY if wclass == "heavy" else ACCENT
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="suggest-card" style="border-left:4px solid '
                        f'{border_color}">'
                        f'<strong style="font-size:0.92em;color:{TEXT}">'
                        f"{c.game}</strong> "
                        f"{weight_badge_html(wclass)}<br>"
                        f'<span style="color:{TEXT_SEC};font-size:0.82em">'
                        f"\U0001f4c5 {day_label} {time_label} &bull; "
                        f"\U0001f4cd {c.location} &bull; "
                        f"\U0001f465 {c.eligible_count}</span><br>"
                        f'<span style="color:{ACCENT};font-size:0.8em">'
                        f"{reason}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # ---- Non-viable section ----
    if non_viable:
        # Group by rejection reason, list game names under each
        reason_games: dict[str, set[str]] = defaultdict(set)
        for c in non_viable:
            reason = c.rejection_reason or "Unknown reason"
            reason_games[reason].add(c.game)

        total_unique = len({c.game for c in non_viable})
        with st.expander(
            f"Can\u2019t be scheduled ({total_unique} games)", expanded=False
        ):
            st.markdown(
                f'<div class="nv-scroll-container">',
                unsafe_allow_html=True,
            )
            for reason, game_names in sorted(
                reason_games.items(), key=lambda r: -len(r[1])
            ):
                chips = " ".join(
                    f'<span class="nv-chip">{g}</span>' for g in sorted(game_names)
                )
                st.markdown(
                    f'<div class="nv-group">'
                    f'<div class="nv-group-reason">{reason}</div>'
                    f'<div class="nv-group-games">{chips}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    return viable
