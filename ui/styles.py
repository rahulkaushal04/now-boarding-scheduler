"""Design foundation — shared stylesheet, colour palette, and small HTML helpers.

All colours are defined as module-level constants. ``inject_custom_css`` pushes
the shared stylesheet into every Streamlit page. Keep this file the single
source of visual truth — panels should reach for these helpers and constants
rather than hard-coding colours or one-off markup.
"""

import html as _html

import streamlit as st

# ---------------------------------------------------------------------------
# Colour palette — one calm accent colour, used sparingly. Green/amber/red are
# reserved for actual status (done, needs attention, problem) — never decoration.
# ---------------------------------------------------------------------------
PRIMARY = "#5B7FEA"        # actions, active states, links
ACCENT = "#C9922E"         # needs-attention / pending changes
ALERT = "#D6635F"          # problems / can't be scheduled
SUCCESS = "#3FA66E"        # confirmations
SURFACE = "#15171C"        # card / section background
SURFACE_RAISED = "#1B1E25" # hover state
BORDER = "#262A33"
BG = "#0E1013"
TEXT = "#E6E8EB"
TEXT_SEC = "#98A2B3"
TEXT_MUTED = "#666E7D"


def inject_custom_css() -> None:
    """Inject the shared stylesheet into the current Streamlit page."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3 { letter-spacing: -0.01em; }

        /* ---- Page header: plain title + one-line subtitle, no card ---- */
        .page-header { margin-bottom: 1.5rem; }
        .page-header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #E6E8EB;
            margin: 0 0 0.25rem 0;
        }
        .page-header p {
            color: #98A2B3;
            font-size: 0.95rem;
            margin: 0;
        }

        /* ---- Section heading used inside a page (not a full page header) ---- */
        .section-heading {
            font-size: 1.05rem;
            font-weight: 600;
            color: #E6E8EB;
            margin: 1.75rem 0 0.5rem 0;
        }
        .section-note {
            color: #98A2B3;
            font-size: 0.88rem;
            margin: -0.25rem 0 0.75rem 0;
        }

        /* ---- Step indicator ---- */
        .step-bar {
            display: flex;
            align-items: center;
            gap: 0;
            margin-bottom: 1.75rem;
            border-bottom: 1px solid #262A33;
        }
        .step-pill {
            flex: 1;
            text-align: center;
            padding: 0 0 10px 0;
            font-size: 0.88em;
            font-weight: 500;
            color: #666E7D;
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;
        }
        .step-pill.active {
            color: #E6E8EB;
            font-weight: 600;
            border-bottom-color: #5B7FEA;
        }
        .step-pill.done { color: #98A2B3; }
        .step-pill .step-num {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 0.76em;
            font-weight: 600;
            margin-right: 6px;
            vertical-align: middle;
        }
        .step-pill.pending .step-num {
            border: 1.5px solid #3A3F4B;
            color: #666E7D;
        }
        .step-pill.active .step-num {
            background: #5B7FEA;
            color: #0E1013;
        }
        .step-pill.done .step-num {
            background: transparent;
            border: 1.5px solid #98A2B3;
            color: #98A2B3;
        }

        /* ---- Tab styling ---- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            border-bottom: 1px solid #262A33;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 4px;
            font-weight: 500;
            font-size: 0.9em;
            color: #98A2B3;
        }
        .stTabs [aria-selected="true"] {
            color: #E6E8EB !important;
        }

        /* ---- Settings panel (upload step sidebar) ---- */
        .settings-card {
            background: #15171C;
            border: 1px solid #262A33;
            border-radius: 10px;
            padding: 1.1rem 1.25rem;
        }
        .settings-title {
            font-size: 0.95em;
            font-weight: 600;
            color: #E6E8EB;
            margin-bottom: 0.9rem;
        }

        /* ---- Plain confirmation line (replaces stat-card grids) ---- */
        .confirm-line {
            color: #98A2B3;
            font-size: 0.9rem;
            margin: 0.5rem 0 1rem 0;
        }
        .confirm-line strong { color: #E6E8EB; font-weight: 600; }

        /* ---- Neutral text tag (weight class, "2nd table", etc.) ---- */
        .tag {
            color: #98A2B3;
            font-size: 0.8em;
            font-weight: 500;
        }
        .tag.tag-attention { color: #C9922E; }

        /* ---- Timetable session card ---- */
        .rec-card {
            background: #15171C;
            border: 1px solid #262A33;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.5rem;
        }
        .rec-card-title {
            font-weight: 600;
            font-size: 0.95em;
            color: #E6E8EB;
        }
        .rec-card-meta {
            color: #98A2B3;
            font-size: 0.82em;
            margin-top: 2px;
        }

        /* ---- Empty state ---- */
        .empty-state {
            text-align: center;
            padding: 2.5rem 1rem;
            color: #666E7D;
            font-size: 0.95em;
        }
        .notice-box {
            background: #15171C;
            border: 1px solid #262A33;
            border-radius: 8px;
            padding: 1.25rem;
            text-align: center;
            color: #98A2B3;
        }

        div[data-testid="stExpander"] {
            border: 1px solid #262A33;
            border-radius: 8px;
        }

        .stButton > button { border-radius: 6px; }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background-color: #5B7FEA;
            border-color: #5B7FEA;
            color: #0E1013;
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background-color: #4A6BD4;
            border-color: #4A6BD4;
        }

        /* ---- Upload file-uploader tweaks ---- */
        div[data-testid="stFileUploader"] { margin-bottom: 0rem !important; }
        div[data-testid="stFileUploader"] section { padding: 0.5rem !important; }

        /* ---- Game Rules: pending-changes notice ---- */
        .rules-changes-bar {
            display: flex;
            align-items: center;
            background: rgba(201, 146, 46, 0.08);
            border: 1px solid rgba(201, 146, 46, 0.25);
            border-radius: 8px;
            padding: 0.55rem 1rem;
            margin: 0.75rem 0 0.5rem 0;
        }
        .rules-changes-count {
            color: #C9922E;
            font-weight: 600;
            font-size: 0.88em;
        }
        .change-tag {
            background: rgba(201, 146, 46, 0.12);
            color: #C9922E;
            padding: 1px 7px;
            border-radius: 4px;
            font-size: 0.76em;
            font-weight: 500;
            margin-right: 4px;
            display: inline-block;
        }

        /* ---- Recommendations: suggestion card ---- */
        .suggest-card {
            background: #15171C;
            border: 1px solid #262A33;
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            margin-bottom: 0.4rem;
        }

        /* ---- Recommendations: can't-be-scheduled, grouped by reason ---- */
        .nv-scroll-container {
            max-height: 360px;
            overflow-y: auto;
            padding-right: 0.25rem;
        }
        .nv-group {
            border-left: 2px solid #D6635F;
            padding: 0.4rem 0 0.4rem 0.75rem;
            margin-bottom: 0.6rem;
        }
        .nv-group-reason {
            color: #98A2B3;
            font-size: 0.85em;
            margin-bottom: 0.3rem;
        }
        .nv-group-games {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
        }
        .nv-chip {
            background: #1B1E25;
            color: #E6E8EB;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    """Render a plain page title with an optional one-line subtitle.

    No card, border, or background — just a title and quiet supporting
    text, matching how a real product labels the screen the user is on.

    Args:
        title (str): Page title.
        subtitle (str): Optional one-line description. Omit if the title
            is already self-explanatory.

    Example:
        >>> page_header("Recommendations", "Your schedule for the week.")
    """
    safe_title = _html.escape(title)
    sub_html = f"<p>{_html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="page-header"><h1>{safe_title}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section_heading(title: str, note: str = "") -> None:
    """Render an in-page section heading, smaller than a page header.

    Args:
        title (str): Section title.
        note (str): Optional one-line clarifying note under the title.
    """
    st.markdown(f'<div class="section-heading">{_html.escape(title)}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{_html.escape(note)}</div>', unsafe_allow_html=True)


def weight_tag_html(weight_class: str) -> str:
    """Return a plain-text weight-class tag ("Heavy" / "Medium"), no colour coding.

    Args:
        weight_class (str): ``"heavy"`` or ``"medium"``.

    Returns:
        str: Small HTML ``<span>`` with the label.

    Example:
        >>> "Heavy" in weight_tag_html("heavy")
        True
    """
    label = "Heavy" if weight_class == "heavy" else "Medium"
    return f'<span class="tag">{label}</span>'
