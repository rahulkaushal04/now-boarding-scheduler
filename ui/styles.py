"""Design foundation — dark-mode CSS, colour constants, HTML helpers."""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------
PRIMARY = "#00D4AA"
PRIMARY_MUTED = "#00A88A"
ACCENT = "#FFB830"
ALERT = "#FF6B6B"
WARNING = "#FFA726"
SUCCESS = "#69F0AE"
SURFACE = "#1B1F27"
SURFACE_RAISED = "#262B36"
BORDER = "#2D333B"
BG = "#0E1117"
TEXT = "#E6E6E6"
TEXT_SEC = "#9CA3AF"
TEXT_MUTED = "#6B7280"

HEAVY_COLOR = PRIMARY
MEDIUM_COLOR = ACCENT


# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------
def inject_custom_css() -> None:
    """Inject dark-mode card styles, score bars, badges."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .session-card {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
        }
        .session-card:hover {
            background: #262B36;
            transition: background 0.2s ease;
        }
        .tag-heavy { border-left: 4px solid #00D4AA; }
        .tag-medium { border-left: 4px solid #FFB830; }

        .score-bar {
            background: #262B36;
            border-radius: 6px;
            overflow: hidden;
            height: 8px;
            width: 100%;
            margin: 4px 0;
        }
        .score-fill {
            background: #00D4AA;
            height: 8px;
            border-radius: 6px;
        }

        .badge-accepted {
            background: rgba(105, 240, 174, 0.15);
            color: #69F0AE;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            display: inline-block;
        }
        .badge-rejected {
            background: rgba(255, 107, 107, 0.15);
            color: #FF6B6B;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            display: inline-block;
        }
        .badge-weight {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            display: inline-block;
        }
        .badge-heavy {
            background: rgba(0, 212, 170, 0.15);
            color: #00D4AA;
        }
        .badge-medium {
            background: rgba(255, 184, 48, 0.15);
            color: #FFB830;
        }

        .summary-card {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-radius: 12px;
            padding: 1.25rem;
            margin: 0.5rem 0;
        }

        .coverage-counter {
            font-size: 1.1em;
            color: #9CA3AF;
            margin-top: 0.5rem;
        }

        div[data-testid="stExpander"] {
            border: 1px solid #2D333B;
            border-radius: 8px;
        }

        .stButton > button {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def score_bar_html(score: float) -> str:
    """Return HTML for a horizontal score bar (0-1 → 0-100 %)."""
    pct = max(0.0, min(100.0, score * 100))
    return (
        f'<div class="score-bar">'
        f'<div class="score-fill" style="width:{pct:.0f}%"></div>'
        f"</div>"
        f'<span style="color:{TEXT_SEC};font-size:0.85em">{pct:.0f}%</span>'
    )


def badge_html(text: str, color: str) -> str:
    """Return an inline coloured badge."""
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<span style="background:rgba({r},{g},{b},0.15);color:{color};'
        f"padding:2px 8px;border-radius:4px;font-size:0.85em;"
        f'font-weight:600;display:inline-block">{text}</span>'
    )


def weight_badge_html(weight_class: str) -> str:
    """Return a Heavy / Medium weight-class badge."""
    if weight_class == "heavy":
        return badge_html("Heavy", PRIMARY)
    return badge_html("Medium", ACCENT)
