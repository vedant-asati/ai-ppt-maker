"""Presentation planning, narrative structure, audience profiles, and validation."""

from .planner import Planner
from .validator import ContentValidator
from .content_scorer import ContentScorer, score_and_print
from .source_analyzer import SourceAnalyzer, analyze_source
from .narrative_arcs import NARRATIVE_ARCS, arc_for_prompt
from .audience_profiles import AUDIENCE_PROFILES, profile_for_prompt

__all__ = [
    "Planner",
    "ContentValidator",
    "ContentScorer",
    "score_and_print",
    "SourceAnalyzer",
    "analyze_source",
    "NARRATIVE_ARCS",
    "arc_for_prompt",
    "AUDIENCE_PROFILES",
    "profile_for_prompt",
]
