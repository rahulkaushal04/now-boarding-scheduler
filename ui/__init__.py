"""UI panels for the Now Boarding Scheduler Streamlit app."""

from ui.styles import inject_custom_css, page_header, section_heading, weight_tag_html
from ui.upload_panel import render_upload_section
from ui.insights_panel import render_insights
from ui.game_rules_panel import render_game_rules
from ui.recommend_panel import render_recommendations

__all__ = [
    "inject_custom_css",
    "page_header",
    "section_heading",
    "weight_tag_html",
    "render_upload_section",
    "render_game_rules",
    "render_recommendations",
    "render_insights",
]
