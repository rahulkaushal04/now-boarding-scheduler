"""Step 3 — Recommendations: timetable view of best sessions.

Renders a day × location grid of the sessions selected by the engine,
plus near-miss suggestions for games that almost made the schedule.
"""

from collections import defaultdict

import streamlit as st

from models.entities import CandidateSession, Game, Player, Slot
from ui.styles import TEXT_SEC, page_header, weight_tag_html

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
    slots: dict[str, Slot] | None = None,
    suggestions: list[CandidateSession] | None = None,
) -> list[CandidateSession]:
    """Render the recommendation panel as a day × location timetable.

    Args:
        candidates: Selected (viable) sessions from the engine.
        all_players: Full player dict for coverage stats.
        games: Game objects keyed by id.
        slots: Slot objects for day/time resolution.
        suggestions: Near-miss candidates that almost made the schedule.

    Returns:
        List of viable sessions shown in the timetable.
    """
    slots = slots or {}
    suggestions = suggestions or []

    viable = [c for c in candidates if c.viable]

    page_header("Recommendations", "Your schedule for the week, built from player votes and availability.")

    if not viable:
        st.markdown(
            '<div class="empty-state">No recommendations right now.<br>'
            "Try changing the game rules or settings.</div>",
            unsafe_allow_html=True,
        )
        return []

    # ---- One-line summary ----
    covered_players = {p for c in viable for p in c.assigned_players}
    st.markdown(
        f'<div class="confirm-line">This schedule runs '
        f"<strong>{len(viable)}</strong> session{'s' if len(viable) != 1 else ''} "
        f"and serves <strong>{len(covered_players)} of {len(all_players)}</strong> players.</div>",
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
            f'font-weight:600;font-size:var(--nb-fs-sm)">Place</div>',
            unsafe_allow_html=True,
        )
    for i, day in enumerate(sorted_days):
        with header_cols[i + 1]:
            st.markdown(
                '<div style="padding:0.5rem 0;'
                'font-weight:600;font-size:var(--nb-fs-sm);text-align:center">'
                f"{day}</div>",
                unsafe_allow_html=True,
            )

    # Data rows
    for loc in sorted_locs:
        row_cols = st.columns([1] + [2] * len(sorted_days))
        with row_cols[0]:
            st.markdown(
                f'<div style="padding:0.6rem 0;color:{TEXT_SEC};'
                f'font-size:var(--nb-fs-sm);font-weight:500">{loc}</div>',
                unsafe_allow_html=True,
            )
        for i, day in enumerate(sorted_days):
            with row_cols[i + 1]:
                sessions = grid.get((day, loc), [])
                if not sessions:
                    st.markdown(
                        '<div style="padding:0.6rem;text-align:center;'
                        f'color:{TEXT_SEC};font-size:var(--nb-fs-sm);opacity:0.4">—</div>',
                        unsafe_allow_html=True,
                    )
                    continue
                for c in sessions:
                    wc = games.get(c.game)
                    wclass = wc.weight_class if wc else "medium"
                    slot_obj = slots.get(c.slot)
                    time_label = slot_obj.time if slot_obj else c.slot
                    overflow_tag = (
                        ' <span class="tag tag-attention">2nd table</span>'
                        if c.is_overflow
                        else ""
                    )
                    st.markdown(
                        f'<div class="rec-card">'
                        f'<div class="rec-card-title">{c.game}</div>'
                        f'<div class="rec-card-meta">{time_label} '
                        f"&middot; {c.assigned_count} players "
                        f"&middot; {weight_tag_html(wclass)}{overflow_tag}</div>"
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
            cols = st.columns(2)
            for i, c in enumerate(unique_suggestions):
                wc = games.get(c.game)
                wclass = wc.weight_class if wc else "medium"
                slot_obj = slots.get(c.slot)
                time_label = slot_obj.time if slot_obj else c.slot
                day_label = slot_obj.day if slot_obj else ""
                reason = c.suggestion_reason or "Didn't fit in the schedule"
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="suggest-card">'
                        f'<div class="rec-card-title">{c.game} '
                        f"{weight_tag_html(wclass)}</div>"
                        f'<div class="rec-card-meta">{day_label} {time_label} '
                        f"&middot; {c.location} &middot; "
                        f"{c.eligible_count} interested</div>"
                        f'<div style="color:{TEXT_SEC};font-size:0.82em;margin-top:0.3rem">'
                        f"{reason}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    return viable
