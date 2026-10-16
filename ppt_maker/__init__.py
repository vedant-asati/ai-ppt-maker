"""
AI Presentation Agency (ppt_maker)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An autonomous, multi-stage presentation engineering pipeline that synthesizes
studio-grade, themed presentations in vector PDF and editable PPTX formats.
"""

__version__ = "1.0.0"

from .core.schemas import (
    MasterPlan,
    Slide,
    Theme,
    ContentBlock,
    BulletBlock,
    StatBlock,
    PullQuoteBlock,
    ComparisonBlock,
    StepBlock,
    CalloutBlock,
    KeyValueBlock,
)
from .core.config_manager import ConfigManager
from .core.api_keys import get_api_keys, get_client, rotate_client

from .planning.planner import Planner
from .planning.validator import ContentValidator
from .planning.content_scorer import ContentScorer, score_and_print
from .planning.source_analyzer import SourceAnalyzer, analyze_source
from .planning.narrative_arcs import NARRATIVE_ARCS, arc_for_prompt
from .planning.audience_profiles import AUDIENCE_PROFILES, profile_for_prompt

from .design.theme_palettes import PALETTES, DEFAULT_PALETTE, PALETTE_MANAGED_THEMES
from .design.theme_resolver import ThemeResolver
from .design.gradient_generator import GradientGenerator
from .design.font_downloader import download_fonts

from .imaging.image_generator import ImageGenerator
from .imaging.image_matcher import ImageMatcher
from .imaging.image_cache import ImageCache
from .imaging.image_validator import ImageValidator, ImageIssue

from .rendering.templater import Templater
from .rendering.renderer import Renderer

from .export.compiler import Compiler
from .export.pptx_exporter import PptxExporter

from .audit.quality_checker import QualityChecker

__all__ = [
    # Core
    "MasterPlan",
    "Slide",
    "Theme",
    "ContentBlock",
    "BulletBlock",
    "StatBlock",
    "PullQuoteBlock",
    "ComparisonBlock",
    "StepBlock",
    "CalloutBlock",
    "KeyValueBlock",
    "ConfigManager",
    "get_api_keys",
    "get_client",
    "rotate_client",
    # Planning
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
    # Design
    "PALETTES",
    "DEFAULT_PALETTE",
    "PALETTE_MANAGED_THEMES",
    "ThemeResolver",
    "GradientGenerator",
    "download_fonts",
    # Imaging
    "ImageGenerator",
    "ImageMatcher",
    "ImageCache",
    "ImageValidator",
    "ImageIssue",
    # Rendering
    "Templater",
    "Renderer",
    # Export
    "Compiler",
    "PptxExporter",
    # Audit
    "QualityChecker",
]
