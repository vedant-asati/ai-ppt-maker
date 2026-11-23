"""
orchestrator.py — Main MultiAgentPlanner entrypoint.
Coordinates DeckArchitect, BatchedSynthesizer, DeterministicGatekeeper,
and ContentValidator into a unified MasterPlan generation pipeline.
"""

from typing import Union, Optional
from ppt_maker.core.api_keys import APIKeyRotator, get_rotator
from ppt_maker.core.schemas import MasterPlan, Theme
from ppt_maker.design.theme_resolver import ThemeResolver
from ppt_maker.planning.validator import ContentValidator
from ppt_maker.planning.multi_agent.stages import (
    DeckArchitect, BatchedSynthesizer, DeterministicGatekeeper
)


class MultiAgentPlanner:
    """
    High-level coordinator orchestrating the multi-agent planning workflow:
      Stage 1: DeckArchitect (Narrative Strategy & Layout Blueprints)
      Stage 2: BatchedSynthesizer (Parallel Slide Content Generation with Key Rotation)
      Stage 3: DeterministicGatekeeper (Static Slot Budget Clamping)
      Stage 4: Validation & Theme Resolution
    """

    def __init__(self, rotator: Optional[APIKeyRotator] = None, max_workers: int = 2):
        self.rotator = rotator or get_rotator()
        self.architect = DeckArchitect(self.rotator)
        self.synthesizer = BatchedSynthesizer(self.rotator, max_workers=max_workers)

    def generate_master_plan(self, config: Union[dict, object]) -> MasterPlan:
        # Normalize config to dict if needed
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else (config if isinstance(config, dict) else {})
        source_text = config_dict.get('source_text', '') or ''
        source_file = config_dict.get('source_file', '')

        # If source_file exists, read text
        if source_file:
            import os
            if os.path.isfile(source_file):
                try:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        source_text += "\n\n" + f.read()
                except Exception:
                    pass

        print("\n=== MULTI-AGENT PRESENTATION PLANNING PIPELINE ===")
        print(f"Available Gemini API Keys: {self.rotator.key_count}")

        try:
            # ── Stage 1: Deck Architect ──────────────────────────────────────
            deck_blueprint = self.architect.plan_deck(config_dict, source_text=source_text)
            print(f"  [DeckArchitect] Blueprint generated: '{deck_blueprint.deck_title}' ({len(deck_blueprint.slides)} slides)")
            print(f"  [DeckArchitect] Thesis: {deck_blueprint.thematic_thesis[:100]}...")

            # ── Stage 2: Parallel Batch Synthesis ────────────────────────────
            slides = self.synthesizer.synthesize_slides(deck_blueprint.slides, deck_blueprint, config_dict)

            # ── Stage 3: Static Character Clamping ───────────────────────────
            clamped_slides, violations = DeterministicGatekeeper.audit_and_clamp(slides, deck_blueprint.slides)
            if violations:
                print(f"  [DeterministicGatekeeper] Clamped {len(violations)} slot boundary violations at word boundaries.")

            # ── Stage 4: Theme Resolution ────────────────────────────────────
            design_pref = config_dict.get('design_preferences', {})
            user_theme = design_pref.get('theme_style')
            theme_style = user_theme if user_theme else (deck_blueprint.recommended_theme or 'corporate_clean')
            palette = deck_blueprint.recommended_palette or design_pref.get('palette', None)
            user_color = design_pref.get('primary_color', None)

            css_vars, resolved_palette = ThemeResolver.resolve(
                structural_class=theme_style,
                palette_name=palette,
                ai_css_vars={},
                user_color=user_color
            )

            theme = Theme(
                structural_class=theme_style,
                palette=resolved_palette,
                css_variables=css_vars
            )

            master_plan = MasterPlan(
                theme=theme,
                slides=clamped_slides
            )

            # ── Stage 5: Content Validator ───────────────────────────────────
            validated_plan = ContentValidator.validate_and_prune(master_plan)
            print("  [MultiAgentPlanner] MasterPlan synthesis complete.\n")
            return validated_plan

        except Exception as e:
            print(f"  [MultiAgentPlanner] Critical error during multi-agent DAG: {e}")
            print("  [MultiAgentPlanner] Falling back to standard single-shot Planner...")
            from ppt_maker.planning.planner import Planner
            single_planner = Planner()
            return single_planner.generate_master_plan(config)
