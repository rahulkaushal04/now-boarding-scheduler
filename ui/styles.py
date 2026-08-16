"""Design foundation — shared stylesheet, colour palette, and small HTML helpers.

Everything here follows a constrained system rather than one-off values:
a 6-step spacing scale, a 5-step type scale, and one accent colour used
sparingly. Panels should reach for these helpers and constants — and the
CSS custom properties they inject — rather than hard-coding new sizes or
colours. Consistency, not decoration, is what makes an interface read as
"built by a professional" rather than "assembled from parts."
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

        :root {
            /* Type scale — 5 sizes, nothing in between */
            --nb-fs-xs: 0.75rem;     /* 12px: tags, fine print */
            --nb-fs-sm: 0.8125rem;   /* 13px: secondary text, meta, help */
            --nb-fs-base: 0.9375rem; /* 15px: body */
            --nb-fs-lg: 1.25rem;     /* 20px: section heading */
            --nb-fs-xl: 1.75rem;     /* 28px: page title */

            /* Spacing scale — 4px base unit */
            --nb-sp-1: 0.25rem;  /* 4px */
            --nb-sp-2: 0.5rem;   /* 8px */
            --nb-sp-3: 0.75rem;  /* 12px */
            --nb-sp-4: 1rem;     /* 16px */
            --nb-sp-5: 1.5rem;   /* 24px */
            --nb-sp-6: 2rem;     /* 32px */

            --nb-primary: #5B7FEA;
            --nb-accent: #C9922E;
            --nb-alert: #D6635F;
            --nb-success: #3FA66E;
            --nb-surface: #15171C;
            --nb-surface-raised: #1B1E25;
            --nb-border: #262A33;
            --nb-bg: #0E1013;
            --nb-text: #E6E8EB;
            --nb-text-sec: #98A2B3;
            --nb-text-muted: #666E7D;
            --nb-radius: 8px;
        }

        html {
            /* Bumps every rem-based size in the app (both the custom scale
               above and Streamlit's own built-in widget styles) up from the
               16px browser default — the whole app read too small at 16px. */
            font-size: 18px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3 { letter-spacing: -0.01em; }

        /* ---- Page header: plain title + one-line subtitle, no card ---- */
        .page-header { margin-bottom: var(--nb-sp-5); }
        .page-header h1 {
            font-size: var(--nb-fs-xl);
            font-weight: 700;
            color: var(--nb-text);
            margin: 0 0 var(--nb-sp-1) 0;
            line-height: 1.25;
        }
        .page-header p {
            color: var(--nb-text-sec);
            font-size: var(--nb-fs-base);
            margin: 0;
        }

        /* ---- Section heading used inside a page (not a full page header) ---- */
        .section-heading {
            font-size: var(--nb-fs-lg);
            font-weight: 600;
            color: var(--nb-text);
            margin: var(--nb-sp-6) 0 var(--nb-sp-2) 0;
        }
        .section-note {
            color: var(--nb-text-sec);
            font-size: var(--nb-fs-sm);
            margin: calc(-1 * var(--nb-sp-1)) 0 var(--nb-sp-3) 0;
        }

        /* ---- Step indicator ---- */
        .step-bar {
            display: flex;
            align-items: center;
            gap: 0;
            margin-bottom: var(--nb-sp-5);
            border-bottom: 1px solid var(--nb-border);
        }
        .step-pill {
            flex: 1;
            text-align: center;
            padding: 0 0 var(--nb-sp-2) 0;
            font-size: var(--nb-fs-sm);
            font-weight: 500;
            color: var(--nb-text-muted);
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;
        }
        .step-pill.active {
            color: var(--nb-text);
            font-weight: 600;
            border-bottom-color: var(--nb-primary);
        }
        .step-pill.done { color: var(--nb-text-sec); }
        .step-pill .step-num {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: var(--nb-fs-xs);
            font-weight: 600;
            margin-right: var(--nb-sp-2);
            vertical-align: middle;
        }
        .step-pill.pending .step-num {
            border: 1.5px solid #3A3F4B;
            color: var(--nb-text-muted);
        }
        .step-pill.active .step-num {
            background: var(--nb-primary);
            color: var(--nb-bg);
        }
        .step-pill.done .step-num {
            background: transparent;
            border: 1.5px solid var(--nb-text-sec);
            color: var(--nb-text-sec);
        }

        /* ---- Tab styling ---- */
        .stTabs [data-baseweb="tab-list"] {
            gap: var(--nb-sp-1);
            border-bottom: 1px solid var(--nb-border);
        }
        .stTabs [data-baseweb="tab"] {
            padding: var(--nb-sp-2) var(--nb-sp-1);
            font-weight: 500;
            font-size: var(--nb-fs-sm);
            color: var(--nb-text-sec);
        }
        .stTabs [aria-selected="true"] {
            color: var(--nb-text) !important;
        }

        /* ---- Settings panel (upload step sidebar) ---- */
        .settings-title {
            font-size: var(--nb-fs-base);
            font-weight: 600;
            color: var(--nb-text);
            margin-bottom: var(--nb-sp-3);
        }

        /* ---- Plain confirmation line (replaces stat-card grids) ---- */
        .confirm-line {
            color: var(--nb-text-sec);
            font-size: var(--nb-fs-sm);
            margin: var(--nb-sp-2) 0 var(--nb-sp-4) 0;
        }
        .confirm-line strong { color: var(--nb-text); font-weight: 600; }

        /* ---- Neutral text tag (weight class, "2nd table", etc.) ---- */
        .tag {
            color: var(--nb-text-sec);
            font-size: var(--nb-fs-xs);
            font-weight: 500;
        }
        .tag.tag-attention { color: var(--nb-accent); }

        /* ---- Timetable session card ---- */
        .rec-card {
            background: var(--nb-surface);
            border: 1px solid var(--nb-border);
            border-radius: var(--nb-radius);
            padding: var(--nb-sp-3) var(--nb-sp-4);
            margin-bottom: var(--nb-sp-2);
        }
        .rec-card-title {
            font-weight: 600;
            font-size: var(--nb-fs-base);
            color: var(--nb-text);
        }
        .rec-card-meta {
            color: var(--nb-text-sec);
            font-size: var(--nb-fs-sm);
            margin-top: var(--nb-sp-1);
        }

        /* ---- Empty state ---- */
        .empty-state {
            text-align: center;
            padding: var(--nb-sp-6) var(--nb-sp-4);
            color: var(--nb-text-muted);
            font-size: var(--nb-fs-base);
        }
        .notice-box {
            background: var(--nb-surface);
            border: 1px solid var(--nb-border);
            border-radius: var(--nb-radius);
            padding: var(--nb-sp-5);
            text-align: center;
            color: var(--nb-text-sec);
            font-size: var(--nb-fs-base);
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--nb-border);
            border-radius: var(--nb-radius);
        }

        .stButton > button { border-radius: 6px; font-size: var(--nb-fs-sm); }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background-color: var(--nb-primary);
            border-color: var(--nb-primary);
            color: var(--nb-bg);
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background-color: #4A6BD4;
            border-color: #4A6BD4;
        }

        /* ---- Upload file-uploader tweaks ---- */
        div[data-testid="stFileUploader"] { margin-bottom: 0rem !important; }
        div[data-testid="stFileUploader"] section { padding: var(--nb-sp-2) !important; }

        /* ---- Game Rules: pending-changes notice ---- */
        .rules-changes-bar {
            display: flex;
            align-items: center;
            background: rgba(201, 146, 46, 0.08);
            border: 1px solid rgba(201, 146, 46, 0.25);
            border-radius: var(--nb-radius);
            padding: var(--nb-sp-2) var(--nb-sp-4);
            margin: var(--nb-sp-3) 0 var(--nb-sp-2) 0;
        }
        .rules-changes-count {
            color: var(--nb-accent);
            font-weight: 600;
            font-size: var(--nb-fs-sm);
        }
        .change-tag {
            background: rgba(201, 146, 46, 0.12);
            color: var(--nb-accent);
            padding: 1px 7px;
            border-radius: 4px;
            font-size: var(--nb-fs-xs);
            font-weight: 500;
            margin-right: var(--nb-sp-1);
            display: inline-block;
        }

        /* ---- Recommendations: suggestion card ---- */
        .suggest-card {
            background: var(--nb-surface);
            border: 1px solid var(--nb-border);
            border-radius: var(--nb-radius);
            padding: var(--nb-sp-3) var(--nb-sp-4);
            margin-bottom: var(--nb-sp-2);
        }

        /* ---- Dataframes: sit flush with the rest of the page ---- */
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--nb-border);
            border-radius: var(--nb-radius);
            overflow: hidden;
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
