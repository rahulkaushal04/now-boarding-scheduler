"""Design foundation — dark-mode CSS, colour palette, and HTML helpers.

All brand colours are defined as module-level constants.  ``inject_custom_css``
pushes the shared stylesheet into every Streamlit page, while the
``badge_html`` / ``weight_badge_html`` helpers produce small HTML fragments
used throughout the UI panels.
"""

import html as _html

import streamlit as st

# Colour palette
PRIMARY = "#00D4AA"
ACCENT = "#FFB830"
ALERT = "#FF6B6B"
SUCCESS = "#69F0AE"
SURFACE = "#1B1F27"
SURFACE_RAISED = "#262B36"
BORDER = "#2D333B"
BG = "#0E1117"
TEXT = "#E6E6E6"
TEXT_SEC = "#9CA3AF"
TEXT_MUTED = "#6B7280"


def inject_custom_css() -> None:
    """Inject the shared dark-mode stylesheet into the current Streamlit page.

    Covers step indicators, cards, badges, score bars, recommendation
    panels, and game-rules change-tracking components.
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ---- Step indicator ---- */
        .step-bar {
            display: flex;
            align-items: center;
            gap: 0;
            margin-bottom: 1.5rem;
            background: #1B1F27;
            border-radius: 12px;
            padding: 6px;
            border: 1px solid #2D333B;
        }
        .step-pill {
            flex: 1;
            text-align: center;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 0.9em;
            font-weight: 500;
            color: #6B7280;
            transition: all 0.2s ease;
        }
        .step-pill.active {
            background: rgba(0, 212, 170, 0.12);
            color: #00D4AA;
            font-weight: 700;
        }
        .step-pill.done {
            color: #00D4AA;
        }
        .step-pill .step-num {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            font-size: 0.8em;
            font-weight: 700;
            margin-right: 6px;
            vertical-align: middle;
        }
        .step-pill.pending .step-num {
            border: 2px solid #6B7280;
            color: #6B7280;
        }
        .step-pill.active .step-num {
            background: #00D4AA;
            color: #0E1117;
        }
        .step-pill.done .step-num {
            background: rgba(0, 212, 170, 0.2);
            color: #00D4AA;
        }

        /* ---- Hero card ---- */
        .hero-card {
            background: linear-gradient(135deg, #1B1F27 0%, #1a2332 100%);
            border: 1px solid #2D333B;
            border-radius: 14px;
            padding: 1.5rem 2rem;
            margin-bottom: 1.25rem;
            position: relative;
            overflow: hidden;
        }
        .hero-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(0, 212, 170, 0.05) 0%, transparent 70%);
            border-radius: 50%;
        }
        .hero-title {
            font-size: 1.25em;
            font-weight: 700;
            color: #E6E6E6;
            margin-bottom: 0.3rem;
        }
        .hero-subtitle {
            color: #9CA3AF;
            font-size: 0.92em;
            line-height: 1.5;
        }

        /* ---- Tab styling ---- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: #1B1F27;
            border-radius: 10px;
            padding: 4px;
            border: 1px solid #2D333B;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 0.88em;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(0, 212, 170, 0.1) !important;
        }

        /* ---- Config card ---- */
        .config-card {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-radius: 12px;
            padding: 1.25rem;
        }
        .config-title {
            font-size: 1.05em;
            font-weight: 700;
            color: #E6E6E6;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* ---- Stat counters ---- */
        .stat-row {
            display: flex;
            gap: 0.75rem;
            margin: 1rem 0;
        }
        .stat-item {
            flex: 1;
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-radius: 10px;
            padding: 0.85rem 1rem;
            text-align: center;
        }
        .stat-value {
            font-size: 1.6em;
            font-weight: 700;
            color: #00D4AA;
            line-height: 1;
        }
        .stat-label {
            font-size: 0.78em;
            color: #6B7280;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
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
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background-color: #00A88A;
            border-color: #00A88A;
            color: #0E1117;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background-color: #008F74;
            border-color: #008F74;
        }

        /* ---- Upload file-uploader tweaks ---- */
        div[data-testid="stFileUploader"] {
            margin-bottom: 0rem !important;
        }
        div[data-testid="stFileUploader"] section {
            padding: 0.5rem !important;
        }

        /* ---- Game Rules change tracking ---- */
        .rules-changes-bar {
            display: flex;
            align-items: center;
            background: rgba(255, 184, 48, 0.06);
            border: 1px solid rgba(255, 184, 48, 0.2);
            border-radius: 10px;
            padding: 0.6rem 1rem;
            margin: 0.75rem 0 0.5rem 0;
        }
        .rules-changes-count {
            color: #FFB830;
            font-weight: 600;
            font-size: 0.9em;
        }
        .change-tag {
            background: rgba(255, 184, 48, 0.1);
            color: #FFB830;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.78em;
            font-weight: 500;
            margin-right: 4px;
            display: inline-block;
        }
        .modified-game-row {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-left: 3px solid #FFB830;
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin-bottom: 0.4rem;
        }

        /* ---- Rec panel: schedule strip ---- */
        .schedule-strip {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.75rem;
        }
        .schedule-chip {
            background: rgba(105, 240, 174, 0.08);
            border: 1px solid rgba(105, 240, 174, 0.2);
            border-radius: 8px;
            padding: 0.45rem 0.9rem;
            font-size: 0.85em;
            color: #E6E6E6;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .schedule-chip .chip-dot {
            width: 6px; height: 6px; border-radius: 50%;
            display: inline-block;
        }

        /* ---- Rec panel: recommendation card v2 ---- */
        .rec-card {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-radius: 12px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 0.65rem;
            transition: background 0.15s ease;
        }
        .rec-card:hover {
            background: #262B36;
        }
        .rec-card-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.4rem;
        }
        .rec-card-title {
            font-weight: 700;
            font-size: 1.02em;
            color: #E6E6E6;
        }
        .rec-card-meta {
            color: #9CA3AF;
            font-size: 0.85em;
            display: flex;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }
        .rec-score-row {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }
        .rec-score-row .score-bar { flex: 1; }
        .rec-score-label {
            color: #9CA3AF;
            font-size: 0.82em;
            white-space: nowrap;
        }

        /* ---- Rec panel: non-viable item ---- */
        .nv-item {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-left: 3px solid #FF6B6B;
            border-radius: 8px;
            padding: 0.6rem 1rem;
            margin-bottom: 0.4rem;
            font-size: 0.9em;
        }
        .nv-item strong { color: #E6E6E6; }
        .nv-reason { color: #FF6B6B; font-size: 0.88em; }

        /* ---- Rec panel: empty state ---- */
        .rec-empty {
            text-align: center;
            padding: 2.5rem 1rem;
            color: #6B7280;
            font-size: 0.95em;
        }

        /* ---- Suggestion card (compact) ---- */
        .suggest-card {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-radius: 8px;
            padding: 0.6rem 0.8rem;
            margin-bottom: 0.4rem;
        }

        /* ---- Non-viable: grouped by reason ---- */
        .nv-scroll-container {
            max-height: 360px;
            overflow-y: auto;
            padding-right: 0.25rem;
        }
        .nv-group {
            background: #1B1F27;
            border: 1px solid #2D333B;
            border-left: 3px solid #FF6B6B;
            border-radius: 8px;
            padding: 0.6rem 0.9rem;
            margin-bottom: 0.5rem;
        }
        .nv-group-reason {
            color: #FF6B6B;
            font-size: 0.84em;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }
        .nv-group-games {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
        }
        .nv-chip {
            background: rgba(255, 107, 107, 0.08);
            color: #E6E6E6;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge_html(text: str, color: str) -> str:
    """Return an inline coloured badge ``<span>`` element.

    Computes a semi-transparent background from the hex colour and
    HTML-escapes the label text to prevent injection.

    Args:
        text (str): Label text; HTML-escaped automatically.
        color (str): Hex colour string (e.g. ``"#00D4AA"``).

    Returns:
        str: HTML ``<span>`` string with inline styles applied.

    Example:
        >>> "Heavy" in badge_html("Heavy", "#00D4AA")
        True
    """
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    safe = _html.escape(text)
    return (
        f'<span style="background:rgba({r},{g},{b},0.15);color:{color};'
        f"padding:2px 8px;border-radius:4px;font-size:0.85em;"
        f'font-weight:600;display:inline-block">{safe}</span>'
    )


def weight_badge_html(weight_class: str) -> str:
    """Return a Heavy or Medium weight-class badge HTML string.

    Args:
        weight_class (str): ``"heavy"`` or ``"medium"``.

    Returns:
        str: Coloured HTML badge for the weight class.

    Example:
        >>> "Heavy" in weight_badge_html("heavy")
        True
    """
    if weight_class == "heavy":
        return badge_html("Heavy", PRIMARY)
    return badge_html("Medium", ACCENT)
