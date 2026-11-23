"""
fallback.py — Granular per-slide fallback and error recovery for the multi-agent pipeline.
Guarantees zero full-deck aborts by isolating failures to the affected slide.
"""

import time
import random
import json
from typing import Optional, List
from ppt_maker.core.api_keys import get_client, rotate_client, get_api_keys, APIKeyRotator, get_rotator
from ppt_maker.core.schemas import Slide, SlideBlueprint, BulletBlock, BentoBlock, BentoCard, StatBlock


class PerSlideFallbackHandler:
    """
    Handles isolated per-slide recovery when batch synthesis encounters an error.
    Retries the single failing slide with jittered backoff and key rotation,
    falling back to deterministic heuristic filling if retries are exhausted.
    """

    def __init__(self, rotator: Optional[APIKeyRotator] = None):
        self.rotator = rotator or get_rotator()

    def recover_slide(
        self,
        blueprint: SlideBlueprint,
        deck_info,
        config,
        error: Exception,
        max_retries: int = 2
    ) -> Slide:
        """
        Attempt single-slide recovery using key rotation, falling back to heuristic fill.
        """
        print(f"  [MultiAgent Recovery] Slide {blueprint.slide_number} failed ({error}). Initiating isolated recovery...")

        client, key_idx = self.rotator.get_client()
        for attempt in range(max_retries):
            # Jittered exponential backoff: 0.5s - 1.5s
            sleep_time = (2 ** attempt) * 0.5 + random.uniform(0.1, 0.5)
            time.sleep(sleep_time)

            if client is None:
                break

            try:
                from google.genai import types
                prompt = (
                    f"Synthesize Slide #{blueprint.slide_number} for presentation: '{deck_info.deck_title}'.\n"
                    f"Blueprint directive: {blueprint.title_directive}\n"
                    f"Layout: {blueprint.layout_type} (variant: {blueprint.layout_variant})\n"
                    f"Eyebrow: {blueprint.eyebrow}\n"
                    f"Purpose: {blueprint.slide_purpose}\n"
                    f"Return a single JSON object matching the Slide schema."
                )
                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                        max_output_tokens=1200,
                    )
                )
                text = (response.text or '').strip()
                if text.startswith('```'):
                    lines = text.split('\n')
                    text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
                data = json.loads(text)
                if 'slide' in data and isinstance(data['slide'], dict):
                    data = data['slide']
                from ppt_maker.planning.multi_agent.stages import _normalize_slide_dict
                normalized_data = _normalize_slide_dict(data, blueprint)
                return Slide(**normalized_data)
            except Exception as e:
                print(f"  [MultiAgent Recovery] Single-slide retry {attempt+1}/{max_retries} failed: {e}")
                client, key_idx = self.rotator.rotate_on_error(key_idx)

        print(f"  [MultiAgent Recovery] Retries exhausted for Slide {blueprint.slide_number} → applying deterministic heuristic fill.")
        return self._heuristic_fill(blueprint, deck_info)

    def _heuristic_fill(self, blueprint: SlideBlueprint, deck_info) -> Slide:
        """
        Deterministic, 0ms, zero-token fallback guaranteeing valid Slide construction.
        """
        title = (blueprint.title_directive or f"Slide {blueprint.slide_number}").strip()
        if len(title) > 60:
            title = title[:57] + "..."

        eyebrow = (blueprint.eyebrow or blueprint.slide_purpose.replace('_', ' ').upper())[:30]

        # Generate layout-appropriate content blocks
        if blueprint.layout_type == 'bento':
            cards = [
                BentoCard(
                    card_id="hero",
                    col_span=8,
                    card_style="hero_elevated",
                    badge=eyebrow,
                    title=title,
                    body=f"Key analytical perspective on {blueprint.slide_purpose.replace('_', ' ')}.",
                    accent_svg="marker_highlight"
                ),
                BentoCard(
                    card_id="side_1",
                    col_span=4,
                    card_style="neutral",
                    badge="METRIC",
                    stat_val="99%",
                    stat_label="Reliability Standard"
                ),
                BentoCard(
                    card_id="side_2",
                    col_span=4,
                    card_style="accent_contrast",
                    badge="ACTION",
                    title="Next Step",
                    body="Execute baseline review across key components."
                )
            ]
            content_blocks = [BentoBlock(variant=blueprint.layout_variant or 'bento_8_4', cards=cards)]
        elif blueprint.layout_type == 'stat':
            content_blocks = [
                StatBlock(
                    value="10x",
                    label=title,
                    context=f"Strategic focus for {deck_info.deck_title}."
                )
            ]
        else:
            content_blocks = [
                BulletBlock(items=[
                    f"Primary observation regarding {blueprint.slide_purpose.replace('_', ' ')}.",
                    "Structured analytical outcome validated against core criteria.",
                    "Strategic direction for continued implementation."
                ])
            ]

        return Slide(
            slide_number=blueprint.slide_number,
            layout_type=blueprint.layout_type,
            layout_variant=blueprint.layout_variant,
            title=title,
            subtitle="Deterministic fallback synthesis.",
            eyebrow=eyebrow,
            slide_purpose=blueprint.slide_purpose,
            narrative_weight=blueprint.narrative_weight,
            content_blocks=content_blocks,
            speaker_notes=f"Key takeaway: {title}. Focus on the strategic impact for {deck_info.deck_title}.",
            requires_image=False
        )
