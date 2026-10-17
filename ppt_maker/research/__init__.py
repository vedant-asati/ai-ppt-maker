"""
ppt_maker.research — Grounded Research Agent for presentation topic discovery.
"""

from .searcher import QueryDecomposer, DuckDuckGoSearchProvider
from .synthesizer import ResearchSynthesizer, GroundedBrief, extract_article_content
from .agent import ResearchAgent

__all__ = [
    "QueryDecomposer",
    "DuckDuckGoSearchProvider",
    "ResearchSynthesizer",
    "GroundedBrief",
    "extract_article_content",
    "ResearchAgent",
]
