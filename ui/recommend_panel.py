"""Step 3 — Recommendations: ranked cards with accept / skip."""
from __future__ import annotations

import streamlit as st

from models.entities import CandidateSession, Game
from ui.styles import (
    PRIMARY,
    ACCENT,
    SUCCESS,
    ALERT,
    TEXT_SEC,
    score_bar_html,
    weight_badge_html,
    badge_html,
)


def render_recommendations(
    candidates: list[CandidateSession],
    all_players: dict,
    games: dict[str, Game],
) -> list[CandidateSession]:
    """Render the recommendation panel.

    Shows "Your Schedule" at the top, ranked recommendation cards below,
    and non-viable candidates in a collapsed section.

    Returns the list of accepted ``CandidateSession`` objects.
    """
    st.header("Recommendations")

    # Initialise accepted set
    if "accepted_indices" not in st.session_state:
        st.session_state["accepted_indices"] = set()
    if "skipped_indices" not in st.session_state:
        st.session_state["skipped_indices"] = set()

    accepted_idx: set[int] = st.session_state["accepted_indices"]
    skipped_idx: set[int] = st.session_state["skipped_indices"]

    viable = [c for c in candidates if c.viable]
    non_viable = [c for c in candidates if not c.viable]

    # ---- Your Schedule panel ----
    accepted_sessions = [viable[i] for i in sorted(accepted_idx) if i < len(viable)]
    covered = set()
    for s in accepted_sessions:
        covered.update(s.eligible_players)

    target = st.session_state.get("config_target_sessions", 4)

    st.markdown(
        f'<div class="summary-card">'
        f"<strong style='color:{PRIMARY}'>"
        f"\u2705 Your Schedule ({len(accepted_sessions)} of {target})</strong>",
        unsafe_allow_html=True,
    )
    if accepted_sessions:
        for s in accepted_sessions:
            wc = games.get(s.game)
            wclass = wc.weight_class if wc else "medium"
            tag_class = "tag-heavy" if wclass == "heavy" else "tag-medium"
            st.markdown(
                f'<div class="session-card {tag_class}" style="padding:0.5rem 1rem">'
                f"<strong>{s.game}</strong> &middot; {s.slot} &middot; "
                f"{s.location} &middot; {s.eligible_count} players "
                f'{badge_html("Accepted", SUCCESS)}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f"<span style='color:{TEXT_SEC}'>Accept recommendations below to build your schedule.</span>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="coverage-counter">Coverage: '
        f"<strong>{len(covered)}</strong> of "
        f"<strong>{len(all_players)}</strong> players</div></div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ---- Recommendation cards (viable, not yet accepted/skipped) ----
    shown = 0
    for idx, c in enumerate(viable):
        if idx in accepted_idx or idx in skipped_idx:
            continue

        wc = games.get(c.game)
        wclass = wc.weight_class if wc else "medium"
        tag_class = "tag-heavy" if wclass == "heavy" else "tag-medium"
        total_interested = len(
            st.session_state.get("engine_demand_matrix", {}).get(c.game, set())
        )

        st.markdown(
            f'<div class="session-card {tag_class}">'
            f"<strong>\U0001f3b2 {c.game}</strong> "
            f"{weight_badge_html(wclass)}<br>"
            f"<span style='color:{TEXT_SEC}'>"
            f"\U0001f4c5 {c.slot} &middot; \U0001f4cd {c.location}</span><br>"
            f"<span style='color:{TEXT_SEC}'>"
            f"\U0001f465 {c.eligible_count} eligible"
            f" (of {total_interested} interested)</span><br>"
            f"{score_bar_html(c.viability_score)}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Reasoning expander
        if c.reasoning:
            with st.expander("Why this recommendation?", expanded=False):
                st.markdown(f"**Demand:** {c.reasoning.demand_reason}")
                st.markdown(f"**Overlap:** {c.reasoning.overlap_reason}")
                st.markdown(f"**Selection:** {c.reasoning.selection_reason}")
                if c.reasoning.conflict_note:
                    st.markdown(f"**Conflicts:** {c.reasoning.conflict_note}")
                if c.reasoning.score_breakdown:
                    st.caption("Score breakdown")
                    cols = st.columns(len(c.reasoning.score_breakdown))
                    for ci, (k, v) in enumerate(
                        sorted(c.reasoning.score_breakdown.items())
                    ):
                        cols[ci].metric(k.capitalize(), f"{v:.2f}")

        # Accept / Skip buttons
        bcol1, bcol2, _ = st.columns([1, 1, 4])
        with bcol1:
            if st.button("\u2705 Accept", key=f"accept_{idx}"):
                st.session_state["accepted_indices"].add(idx)
                st.rerun()
        with bcol2:
            if st.button("\u23ed Skip", key=f"skip_{idx}"):
                st.session_state["skipped_indices"].add(idx)
                st.rerun()

        shown += 1

    if shown == 0 and not accepted_sessions:
        st.info("No viable recommendations found. Try adjusting game rules or config.")

    # ---- Non-viable section ----
    if non_viable:
        # De-duplicate non-viable by (game, rejection_reason)
        seen: set[tuple[str, str]] = set()
        unique_non_viable: list[CandidateSession] = []
        for c in non_viable:
            key = (c.game, c.rejection_reason or "")
            if key not in seen:
                seen.add(key)
                unique_non_viable.append(c)

        with st.expander(
            f"Not viable ({len(unique_non_viable)} unique reasons)", expanded=False
        ):
            for c in unique_non_viable:
                st.markdown(
                    f'<div class="session-card" style="border-left:4px solid {ALERT}">'
                    f"<strong>{c.game}</strong> &middot; {c.slot} &middot; {c.location}<br>"
                    f'<span style="color:{ALERT}">{c.rejection_reason}</span></div>',
                    unsafe_allow_html=True,
                )

    return accepted_sessions
