"""Final schedule summary and export (CSV / WhatsApp copy-paste).

Renders accepted sessions as styled cards and provides a downloadable
CSV plus a pre-formatted WhatsApp text block for sharing.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from models.entities import CandidateSession, Game
from ui.styles import SUCCESS, TEXT_SEC, badge_html, weight_badge_html


def render_final_schedule(
    accepted: list[CandidateSession],
    games: dict[str, Game],
) -> None:
    """Render the final accepted schedule with export options.

    Args:
        accepted: Sessions the user accepted from the recommendations step.
        games: Game objects keyed by id (used for weight-class badges).
    """
    st.header("Final Schedule")

    if not accepted:
        st.info(
            "No sessions accepted yet. "
            "Go back to Recommendations to build your schedule."
        )
        return

    # ---- Summary cards ----
    for s in accepted:
        game = games.get(s.game)
        wclass = game.weight_class if game else "medium"
        tag_class = "tag-heavy" if wclass == "heavy" else "tag-medium"
        st.markdown(
            f'<div class="session-card {tag_class}">'
            f"<strong>{s.game}</strong> {weight_badge_html(wclass)} "
            f'{badge_html("Accepted", SUCCESS)}<br>'
            f"<span style='color:{TEXT_SEC}'>"
            f"\U0001f4c5 {s.slot} &middot; \U0001f4cd {s.location} "
            f"&middot; \U0001f465 {s.eligible_count} players"
            f"</span></div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ---- CSV export ----
    export_df = pd.DataFrame(
        [
            {
                "Game": s.game,
                "Weight Class": (
                    games[s.game].weight_class.capitalize() if s.game in games else ""
                ),
                "Slot": s.slot,
                "Location": s.location,
                "Eligible Players": s.eligible_count,
                "Players": ", ".join(sorted(s.eligible_players)),
            }
            for s in accepted
        ]
    )

    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)

    st.download_button(
        label="\U0001f4e5 Download CSV",
        data=csv_buffer.getvalue(),
        file_name="now_boarding_schedule.csv",
        mime="text/csv",
    )

    # ---- WhatsApp-formatted text ----
    lines = ["\U0001f3b2 *Now Boarding \u2014 Weekly Schedule*\n"]
    for s in accepted:
        lines.append(
            f"\U0001f3b2 {s.game} | \U0001f4c5 {s.slot} | "
            f"\U0001f4cd {s.location} | \U0001f465 {s.eligible_count} players"
        )
    wa_text = "\n".join(lines)

    st.text_area(
        "WhatsApp / Copy-Paste",
        value=wa_text,
        height=180,
        help="Copy this text and paste it into your WhatsApp group.",
    )
