from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union, Annotated

# ─────────────────────────────────────────────
# Content Blocks — typed replacements for flat content_bullets
# ─────────────────────────────────────────────

class BulletBlock(BaseModel):
    block_type: Literal['bullets'] = 'bullets'
    items: List[str] = Field(
        description="Concise bullet points. Max 6 items, 120 chars each."
    )

class StatBlock(BaseModel):
    block_type: Literal['stat'] = 'stat'
    value: str = Field(description="The hero number/metric. e.g. '400%', '$2.3B', '10x'")
    label: str = Field(description="Short label. e.g. 'ROI Improvement', 'Annual Revenue'")
    context: Optional[str] = Field(
        default=None,
        description="One-line context. e.g. 'vs. industry average of 120%'"
    )

class PullQuoteBlock(BaseModel):
    block_type: Literal['pullquote'] = 'pullquote'
    quote: str = Field(description="The quote text (without quotation marks).")
    attribution: Optional[str] = Field(
        default=None,
        description="Attribution line. e.g. '— Steve Jobs, Apple'"
    )

class ComparisonBlock(BaseModel):
    block_type: Literal['comparison'] = 'comparison'
    left_label: str = Field(description="e.g. 'Before', 'Traditional', 'Competitor'")
    left_items: List[str] = Field(description="2–4 items for the left column.")
    right_label: str = Field(description="e.g. 'After', 'AI-Assisted', 'Our Approach'")
    right_items: List[str] = Field(description="2–4 items for the right column.")

class StepBlock(BaseModel):
    block_type: Literal['steps'] = 'steps'
    steps: List[str] = Field(
        description="Ordered sequence of steps/phases. 2–5 items, 60 chars each."
    )
    step_labels: Optional[List[str]] = Field(
        default=None,
        description="Optional short label per step (e.g. 'Phase 1'). Same length as steps."
    )

class CalloutBlock(BaseModel):
    block_type: Literal['callout'] = 'callout'
    text: str = Field(description="The highlighted callout text. Max 200 chars.")
    callout_type: Literal['insight', 'warning', 'tip', 'fact'] = Field(
        default='insight',
        description="Determines the accent color of the callout box."
    )

class KeyValuePair(BaseModel):
    key: str = Field(description="The key/property name.")
    value: str = Field(description="The value or metric.")

class KeyValueBlock(BaseModel):
    block_type: Literal['keyvalue'] = 'keyvalue'
    pairs: List[Union[KeyValuePair, dict]] = Field(
        description="List of KeyValuePair objects or {'key': str, 'value': str} pairs. Max 5 pairs."
    )

# Discriminated union for template rendering
ContentBlock = Annotated[
    Union[
        BulletBlock,
        StatBlock,
        PullQuoteBlock,
        ComparisonBlock,
        StepBlock,
        CalloutBlock,
        KeyValueBlock,
    ],
    Field(discriminator='block_type')
]

# ─────────────────────────────────────────────
# Theme & Slide Models
# ─────────────────────────────────────────────

class Theme(BaseModel):
    css_variables: dict = Field(
        description=(
            "Dictionary of CSS variables, e.g. {'--bg': '#FFFFFF', '--primary': '#C8541C'}. "
            "For new palette-managed themes (dark_neon, gradient_flow, editorial, aurora), "
            "only structural_class and palette are required — ThemeResolver fills the rest."
        )
    )
    structural_class: Literal[
        'minimalist',
        'glassmorphism',
        'neo_brutalism',
        'corporate_clean',
        'dark_neon',
        'gradient_flow',
        'editorial',
        'aurora',
    ] = Field(description="CSS class applied to <body> to apply global structural styling.")
    palette: Optional[str] = Field(
        default=None,
        description=(
            "Named color palette within the structural class. "
            "e.g. 'cyber_cyan' for dark_neon, 'violet_sunset' for gradient_flow. "
            "ThemeResolver resolves this to CSS variables."
        )
    )

class Slide(BaseModel):
    slide_number: int
    layout_type: Literal['cover', 'split', 'infographic', 'generic', 'quote', 'stat', 'timeline']
    layout_variant: Optional[Literal['reverse']] = Field(
        default=None,
        description="'reverse' flips a split layout so the image is on the left."
    )
    title: str = Field(description="Title of the slide. Must not be empty. Max 8 words.")
    subtitle: Optional[str] = Field(
        default="",
        description="Optional subtitle. Max 120 chars."
    )
    eyebrow: Optional[str] = Field(
        default=None,
        description=(
            "Short category label above the title. e.g. 'Problem', 'Key Insight', 'Phase 2'. "
            "Max 30 chars. Shown in small caps with accent color."
        )
    )
    slide_purpose: Optional[str] = Field(
        default=None,
        description=(
            "The narrative role of this slide. e.g. 'opening_hook', 'problem_statement', "
            "'evidence', 'solution_intro', 'social_proof', 'call_to_action'. "
            "Used by the content scorer and speaker notes generator."
        )
    )
    narrative_weight: Optional[Literal['light', 'standard', 'heavy']] = Field(
        default='standard',
        description=(
            "'light' = breathing room slide (one big idea, lots of whitespace). "
            "'standard' = normal content density. "
            "'heavy' = dense evidence/data slide."
        )
    )
    # Rich typed content blocks (preferred)
    content_blocks: Optional[List[ContentBlock]] = Field(
        default=None,
        description=(
            "Typed content blocks replacing flat content_bullets. "
            "Use BulletBlock for bullet lists, StatBlock for hero numbers, "
            "PullQuoteBlock for quotes, ComparisonBlock for before/after, "
            "StepBlock for process steps, CalloutBlock for highlights, "
            "KeyValueBlock for spec tables."
        )
    )
    # Legacy flat bullets (kept for backward compat; validator migrates to content_blocks)
    content_bullets: List[str] = Field(
        default_factory=list,
        description=(
            "[LEGACY] Flat bullet list. Prefer content_blocks for richer output. "
            "If content_blocks is populated, this field is ignored in rendering."
        )
    )
    speaker_notes: str = Field(
        default="",
        description="Presenter script for this slide. Aim for 3–5 sentences."
    )
    requires_image: bool = Field(
        default=False,
        description="True if this slide design benefits from a generated background/supporting image."
    )
    image_prompt: Optional[str] = Field(
        default="",
        description=(
            "Detailed image generation prompt. Must include art style, mood, and composition. "
            "No text/logos/watermarks in the image."
        )
    )
    image_role: Optional[Literal['background', 'supporting', 'data', 'decorative', 'panel']] = Field(
        default='background',
        description=(
            "'background' = full-bleed behind content (cover, generic). "
            "'supporting' = beside content (split right half). "
            "'data' = chart/diagram IS the content (replaces card grid in infographic). "
            "'decorative' = low-opacity texture layer. "
            "'panel' = portrait right-panel beside text (generic, infographic, timeline)."
        )
    )
    engagement_prompt: Optional[str] = Field(
        default=None,
        description=(
            "A short reflective question the presenter asks the audience. Max 120 chars. "
            "Connects slide content to the viewer's personal experience. "
            "Rendered as a Mirror Moment CTA card at the bottom of the slide."
        )
    )

class MasterPlan(BaseModel):
    theme: Theme
    slides: List[Slide] = Field(
        description="Array of slides representing the entire presentation."
    )
