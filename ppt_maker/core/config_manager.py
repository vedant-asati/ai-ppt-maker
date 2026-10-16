import os
import sys
import yaml
from typing import Optional, Literal

# Pydantic v2 is the standard in modern projects; fall back gracefully if absent
try:
    from pydantic import BaseModel, Field, field_validator, ValidationError
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic AppConfig models  (only defined if pydantic is installed)
# ─────────────────────────────────────────────────────────────────────────────

if _PYDANTIC_AVAILABLE:

    class PresentationGoals(BaseModel):
        audience: str = "General"
        audience_type: Optional[Literal[
            'investor', 'technical', 'executive', 'academic', 'general'
        ]] = None
        duration_minutes: int = Field(default=10, ge=1, le=120)
        slide_count: Optional[int] = Field(default=None, ge=1, le=50)
        tone: str = 'professional'  # free-form: e.g. 'professional', 'friendly, engaging', etc.
        language: str = "English"
        call_to_action: Optional[str] = None
        narrative_arc: Optional[Literal[
            'problem_solution', 'before_after', 'what_why_how',
            'journey', 'contrast', 'inverted_pyramid', 'showcase'
        ]] = None

    class DesignPreferences(BaseModel):
        theme_style: Literal[
            'minimalist', 'glassmorphism', 'neo_brutalism', 'corporate_clean',
            'dark_neon', 'gradient_flow', 'editorial', 'aurora'
        ] = 'corporate_clean'
        palette: Optional[str] = None
        primary_color: Optional[str] = Field(
            default=None,
            pattern=r'^#[0-9A-Fa-f]{6}$'
        )
        font_size_scale: float = Field(default=1.0, ge=0.5, le=2.0)
        color_mode: Literal['auto', 'dark', 'light'] = 'auto'

    class ImagePreferences(BaseModel):
        art_style: str = "clean vector illustration, modern, professional"
        generate_images: bool = True
        force_regenerate: bool = False

    class ContentGuidelines(BaseModel):
        planner_mode: Literal['single_pass', 'multi_pass'] = 'single_pass'
        max_bullets_per_slide: int = Field(default=5, ge=1, le=8)
        min_slide_content_words: int = Field(default=20, ge=5, le=200)
        enable_content_blocks: bool = True
        enable_stats: bool = True
        enable_quotes: bool = True

    class OutputConfig(BaseModel):
        pdf_filename: str = "presentation.pdf"
        output_dir: str = "."
        export_speaker_notes: bool = True
        speaker_notes_filename: Optional[str] = None

    class PipelineConfig(BaseModel):
        preview_mode: bool = False
        audit_level: Literal['none', 'quick', 'full', 'ai'] = 'none'
        force_regenerate_images: bool = False
        skip_image_generation: bool = False
        renderer_timeout_ms: int = Field(default=15000, ge=5000, le=60000)

    class AppConfig(BaseModel):
        source_text: Optional[str] = None
        source_file: Optional[str] = None
        presentation_goals: PresentationGoals = Field(default_factory=PresentationGoals)
        design_preferences: DesignPreferences = Field(default_factory=DesignPreferences)
        image_preferences: ImagePreferences = Field(default_factory=ImagePreferences)
        content_guidelines: ContentGuidelines = Field(default_factory=ContentGuidelines)
        output: OutputConfig = Field(default_factory=OutputConfig)
        pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

        def get(self, key: str, default=None):
            """Dict-compatible .get() for backward compatibility with raw-dict code."""
            return getattr(self, key, default)

# ─────────────────────────────────────────────────────────────────────────────
# Default config template (written by `python cli.py init`)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG_CONTENT = """\
# AI Presentation Agency — Your Config
# Full reference: config_reference.yaml
# Run: python cli.py init   to regenerate this file

presentation_goals:
  audience: "Angel Investors"
  duration_minutes: 10
  slide_count: 10           # 3-20 slides. Or use CLI: --slides 12
  tone: "professional"
  # audience_type: investor | technical | executive | academic | general
  # narrative_arc: problem_solution | before_after | what_why_how | journey | contrast | showcase

design_preferences:
  # Themes: minimalist | glassmorphism | neo_brutalism | corporate_clean
  #         dark_neon  | gradient_flow | editorial     | aurora
  theme_style: "corporate_clean"
  primary_color: "#1A365D"
  # palette: auto-selected; override with e.g. "cyber_cyan" (dark_neon) or "navy" (editorial)

image_preferences:
  art_style: "hyper-realistic corporate photography, warm lighting, professional"
  generate_images: true

source_text: |
  Your topic or outline goes here. This can be a short summary, a bullet list,
  or even a single sentence — the AI Planner will build the full presentation
  from it. For large documents (PDFs, audio), use source_file instead.

output:
  pdf_filename: "presentation.pdf"
  export_speaker_notes: true

pipeline:
  preview_mode: false        # true = render 3 slides at 960x540 for fast preview
  audit_level: "none"        # none | quick | full | ai
"""


# ─────────────────────────────────────────────────────────────────────────────
# ConfigManager
# ─────────────────────────────────────────────────────────────────────────────

class ConfigManager:

    @staticmethod
    def init_config(config_path: str = "config.yaml") -> bool:
        if os.path.exists(config_path):
            print(f"Error: {config_path} already exists. Refusing to overwrite.")
            return False
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG_CONTENT)
        print(f"✓ Generated {config_path}")
        print("  Edit it with your topic, then run: python cli.py generate")
        return True

    @staticmethod
    def load_and_validate(config_path: str = "config.yaml"):
        """
        Load and parse config.yaml.

        Returns an AppConfig object if pydantic is available and validation passes.
        Falls back to a raw dict (with a warning) if validation fails or pydantic
        is not installed — so the pipeline never crashes due to config changes.
        """
        if not os.path.exists(config_path):
            print(f"Error: {config_path} not found. Run 'python cli.py init' first.")
            sys.exit(1)

        with open(config_path, 'r', encoding='utf-8') as f:
            try:
                raw = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"\nError: Could not parse {config_path} — invalid YAML syntax.")
                print(f"  Hint: Check for missing colons, inconsistent indentation, "
                      f"or unquoted special chars.")
                print(f"  Details: {e}")
                sys.exit(1)

        if not isinstance(raw, dict):
            print(f"Error: {config_path} is empty or malformed. "
                  f"Run 'python cli.py init' to create a fresh one.")
            sys.exit(1)

        if not _PYDANTIC_AVAILABLE:
            print("  [Config] pydantic not installed — using raw dict config.")
            return raw

        try:
            config = AppConfig(**raw)
            return config
        except ValidationError as e:
            print(f"\n  [Config Warning] Config validation failed — falling back to raw dict.")
            print(f"  Errors detected:")
            for err in e.errors():
                loc = ' → '.join(str(x) for x in err['loc'])
                print(f"    {loc}: {err['msg']}")
            print()
            return raw

    @staticmethod
    def get(config, key: str, default=None):
        """
        Unified config access — works for both AppConfig and raw dict.
        Usage: ConfigManager.get(config, 'source_text', '')
        """
        if isinstance(config, dict):
            return config.get(key, default)
        return getattr(config, key, default)
