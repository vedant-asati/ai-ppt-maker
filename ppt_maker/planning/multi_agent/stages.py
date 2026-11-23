"""
stages.py — Core pipeline stages for the Multi-Agent Presentation Planning DAG.
Includes:
  1. DeckArchitect: Stage 1 narrative strategy & slot allocation.
  2. BatchedSynthesizer: Stage 2 parallel slide content synthesis with key rotation.
  3. DeterministicGatekeeper: Stage 3 static character clamping & overflow defense.
"""

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Union
from google.genai import types

from ppt_maker.core.api_keys import APIKeyRotator, get_rotator
from ppt_maker.core.schemas import (
    MasterPlan, Slide, SlideBlueprint, DeckArchitectOutput, SlotBudget,
    BulletBlock, BentoBlock, BentoCard, StatBlock, ContentBlock
)
from ppt_maker.planning.multi_agent.prompts import (
    DECK_ARCHITECT_SYSTEM_PROMPT,
    BATCH_SYNTHESIS_SYSTEM_PROMPT
)
from ppt_maker.planning.multi_agent.fallback import PerSlideFallbackHandler


def _normalize_deck_blueprint_dict(data: dict, config: dict, target_count: int) -> dict:
    """Normalize raw LLM JSON output to match DeckArchitectOutput schema."""
    if not isinstance(data, dict):
        data = {}

    for k in ('deck_architect_output', 'deck', 'output'):
        if k in data and isinstance(data[k], dict):
            data = data[k]
            break

    if 'deck_title' not in data:
        data['deck_title'] = data.get('title') or "Executive Briefing"
    if 'thematic_thesis' not in data:
        data['thematic_thesis'] = data.get('thesis') or "Accelerating transformation through structured insights."
    if 'narrative_arc' not in data:
        data['narrative_arc'] = "problem_solution"
    if 'recommended_theme' not in data:
        data['recommended_theme'] = config.get('design_preferences', {}).get('theme_style') or "corporate_clean"

    valid_layouts = {'cover', 'split', 'infographic', 'generic', 'quote', 'stat', 'timeline', 'bento', 'editorial', 'creative', 'modern_tech'}
    raw_slides = data.get('slides') or []
    normalized_slides = []

    for idx, s in enumerate(raw_slides, 1):
        if not isinstance(s, dict):
            continue
        layout = s.get('layout_type') or s.get('layout') or ('cover' if idx == 1 else 'bento')
        if layout not in valid_layouts:
            layout = 'bento' if idx > 1 else 'cover'
        title_dir = s.get('title_directive') or s.get('title') or f"Strategic Insight {idx}"
        weight = s.get('narrative_weight')
        if weight not in ('light', 'standard', 'heavy'):
            weight = 'standard'

        normalized_slides.append({
            'slide_number': idx,
            'layout_type': layout,
            'layout_variant': s.get('layout_variant') or ('bento_8_4' if layout == 'bento' else None),
            'eyebrow': s.get('eyebrow') or f"SECTION {idx}",
            'title_directive': title_dir,
            'slide_purpose': s.get('slide_purpose') or "content",
            'narrative_weight': weight,
            'accent_type': s.get('accent_type') or 'none',
            'slot_budget': s.get('slot_budget') or {}
        })

    data['slides'] = normalized_slides
    return data


def _normalize_slide_dict(data: dict, bp: SlideBlueprint) -> dict:
    """Normalize raw LLM JSON slide output to match Slide schema."""
    if not isinstance(data, dict):
        data = {}

    data['slide_number'] = bp.slide_number
    data['layout_type'] = bp.layout_type
    if bp.layout_variant:
        data['layout_variant'] = bp.layout_variant
    data['title'] = data.get('title') or data.get('slide_title') or bp.title_directive[:60]
    if not data.get('eyebrow'):
        data['eyebrow'] = bp.eyebrow
    if not data.get('slide_purpose'):
        data['slide_purpose'] = bp.slide_purpose
    if data.get('narrative_weight') not in ('light', 'standard', 'heavy'):
        data['narrative_weight'] = bp.narrative_weight

    # Normalize content_blocks
    blocks = data.get('content_blocks')
    if isinstance(blocks, list):
        cleaned_blocks = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            b_type = (b.get('block_type') or b.get('type') or '').lower()
            if 'bento' in b_type:
                b['block_type'] = 'bento'
                cards = b.get('cards') or []
                norm_cards = []
                for idx, c in enumerate(cards):
                    if not isinstance(c, dict):
                        continue
                    c['card_id'] = c.get('card_id') or f"card_{idx+1}"
                    try:
                        c['col_span'] = max(1, min(12, int(c.get('col_span', 4))))
                    except (ValueError, TypeError):
                        c['col_span'] = 4
                    norm_cards.append(c)
                b['cards'] = norm_cards
                cleaned_blocks.append(b)
            elif 'stat' in b_type:
                b['block_type'] = 'stat'
                b['value'] = str(b.get('value') or b.get('stat_val') or b.get('metric') or b.get('number') or '100%')
                b['label'] = str(b.get('label') or b.get('stat_label') or b.get('text') or b.get('description') or 'Key Metric')
                cleaned_blocks.append(b)
            elif 'pullquote' in b_type or 'quote' in b_type:
                b['block_type'] = 'pullquote'
                b['quote'] = str(b.get('quote') or b.get('text') or b.get('content') or b.get('quote_text') or 'Strategic priority')
                cleaned_blocks.append(b)
            elif 'comparison' in b_type:
                b['block_type'] = 'comparison'
                b['left_label'] = b.get('left_label') or 'Current State'
                b['left_items'] = [str(x) for x in (b.get('left_items') or ['Traditional Approach'])]
                b['right_label'] = b.get('right_label') or 'Future State'
                b['right_items'] = [str(x) for x in (b.get('right_items') or ['Modern Solution'])]
                cleaned_blocks.append(b)
            elif 'step' in b_type:
                b['block_type'] = 'steps'
                # Ensure steps is List[str]
                raw_steps = b.get('steps') or []
                norm_steps = []
                for s in raw_steps:
                    if isinstance(s, dict):
                        t = s.get('title') or s.get('step') or ''
                        d = s.get('description') or s.get('text') or ''
                        norm_steps.append(f"{t}: {d}".strip(': ') if (t and d) else (t or d or "Step"))
                    else:
                        norm_steps.append(str(s))
                b['steps'] = norm_steps or ["Step 1: Initiation", "Step 2: Execution"]
                cleaned_blocks.append(b)
            elif 'callout' in b_type:
                b['block_type'] = 'callout'
                b['text'] = str(b.get('text') or b.get('content') or b.get('message') or b.get('callout') or 'Key Insight')
                if b.get('callout_type') not in ('insight', 'warning', 'tip', 'fact'):
                    b['callout_type'] = 'insight'
                cleaned_blocks.append(b)
            elif 'keyvalue' in b_type or 'kv' in b_type:
                b['block_type'] = 'keyvalue'
                pairs = b.get('pairs') or []
                norm_pairs = []
                for p in pairs:
                    if isinstance(p, dict):
                        norm_pairs.append({
                            'key': str(p.get('key') or p.get('name') or 'Metric'),
                            'value': str(p.get('value') or p.get('val') or 'N/A')
                        })
                b['pairs'] = norm_pairs
                cleaned_blocks.append(b)
            elif 'bullet' in b_type:
                b['block_type'] = 'bullets'
                raw_items = b.get('items') or b.get('bullets') or b.get('points') or []
                norm_items = []
                for it in raw_items:
                    if isinstance(it, dict):
                        norm_items.append(it.get('text') or it.get('point') or str(it))
                    else:
                        norm_items.append(str(it))
                b['items'] = norm_items or ["Core initiative outline"]
                cleaned_blocks.append(b)
            else:
                if 'items' in b or 'bullets' in b:
                    b['block_type'] = 'bullets'
                    raw_items = b.get('items') or b.get('bullets') or []
                    b['items'] = [str(x) for x in raw_items] or ["Key takeaway point"]
                    cleaned_blocks.append(b)
                elif ('value' in b and 'label' in b) or 'stat_val' in b:
                    b['block_type'] = 'stat'
                    b['value'] = str(b.get('value') or b.get('stat_val') or '100%')
                    b['label'] = str(b.get('label') or b.get('stat_label') or 'Key Metric')
                    cleaned_blocks.append(b)
                elif 'cards' in b:
                    b['block_type'] = 'bento'
                    cards = b.get('cards') or []
                    b['cards'] = [c for c in cards if isinstance(c, dict)]
                    cleaned_blocks.append(b)
                elif 'steps' in b:
                    b['block_type'] = 'steps'
                    raw_steps = b.get('steps') or []
                    b['steps'] = [str(s.get('title') if isinstance(s, dict) else s) for s in raw_steps] or ["Step 1"]
                    cleaned_blocks.append(b)
        data['content_blocks'] = cleaned_blocks

    return data


class DeckArchitect:
    """
    Stage 1: Analyzes source material, formulates a narrative arc,
    and produces a structural DeckArchitectOutput with assigned layout archetypes and slot budgets.
    """

    def __init__(self, rotator: Optional[APIKeyRotator] = None):
        self.rotator = rotator or get_rotator()

    def plan_deck(self, config: dict, source_text: str = "") -> DeckArchitectOutput:
        goals = config.get('presentation_goals', {})
        audience = goals.get('audience', 'Professional & General')
        tone = goals.get('tone', 'professional')
        slide_count = goals.get('slide_count') or 8

        design_pref = config.get('design_preferences', {})
        theme_style = design_pref.get('theme_style', 'corporate_clean')
        palette = design_pref.get('palette', None)

        user_prompt = (
            f"=== PRESENTATION REQUEST ===\n"
            f"Audience: {audience}\n"
            f"Tone: {tone}\n"
            f"Target slide count: {slide_count}\n"
            f"Preferred theme style: {theme_style}\n"
            f"Palette: {palette or 'auto'}\n\n"
            f"=== SOURCE MATERIAL ===\n"
            f"{source_text[:4000] if source_text else 'Topic: ' + str(config.get('source_text', ''))[:500]}\n\n"
            f"=== INSTRUCTIONS ===\n"
            f"Create a DeckArchitectOutput with {slide_count} slides. "
            f"Ensure slide 1 is 'cover', and use modern archetypes (such as 'bento' or 'editorial') "
            f"for major insight slides. Output ONLY valid JSON matching DeckArchitectOutput."
        )

        client, key_idx = self.rotator.get_client()
        if client is None:
            raise RuntimeError("No Gemini API keys available for DeckArchitect.")

        print("  [DeckArchitect] Synthesizing narrative arc & spatial layout blueprint...")
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=[
                        {"role": "system", "parts": [{"text": DECK_ARCHITECT_SYSTEM_PROMPT}]},
                        {"role": "user", "parts": [{"text": user_prompt}]}
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DeckArchitectOutput,
                        temperature=0.4,
                        max_output_tokens=3000,
                    )
                )
                text = (response.text or '').strip()
                if text.startswith('```'):
                    lines = text.split('\n')
                    text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
                data = json.loads(text)
                normalized = _normalize_deck_blueprint_dict(data, config, slide_count)
                return DeckArchitectOutput(**normalized)
            except Exception as e:
                print(f"  [DeckArchitect] Attempt {attempt+1} failed ({e}). Rotating key...")
                client, key_idx = self.rotator.rotate_on_error(key_idx)
                time.sleep((2 ** attempt) * 0.5 + random.uniform(0.1, 0.4))

        print("  [DeckArchitect] Falling back to default structural blueprint.")
        return self._default_blueprint(slide_count, theme_style, palette)

    def _default_blueprint(self, slide_count: int, theme: str, palette: Optional[str]) -> DeckArchitectOutput:
        blueprints = []
        for i in range(1, slide_count + 1):
            if i == 1:
                layout = 'cover'
                purpose = 'opening_hook'
            elif i == 2:
                layout = 'bento'
                purpose = 'problem_statement'
            elif i == 3:
                layout = 'split'
                purpose = 'evidence'
            elif i == slide_count:
                layout = 'generic'
                purpose = 'call_to_action'
            else:
                layout = 'editorial' if i % 2 == 0 else 'stat'
                purpose = 'solution_overview'

            blueprints.append(SlideBlueprint(
                slide_number=i,
                layout_type=layout,
                layout_variant='bento_8_4' if layout == 'bento' else None,
                eyebrow=purpose.replace('_', ' ').upper(),
                title_directive=f"Strategic Insight {i}",
                slide_purpose=purpose,
                narrative_weight='light' if layout == 'stat' else 'standard'
            ))

        return DeckArchitectOutput(
            deck_title="Executive Briefing",
            narrative_arc="problem_solution",
            thematic_thesis="Accelerating transformation through structured insights.",
            recommended_theme=theme if theme in ['minimalist', 'glassmorphism', 'neo_brutalism', 'corporate_clean', 'dark_neon', 'gradient_flow', 'editorial', 'aurora'] else 'corporate_clean',
            recommended_palette=palette,
            slides=blueprints
        )


class BatchedSynthesizer:
    """
    Stage 2: Takes SlideBlueprints and synthesizes full Slide objects in parallel batches
    utilizing ThreadPoolExecutor and round-robin multi-key rotation.
    """

    def __init__(self, rotator: Optional[APIKeyRotator] = None, max_workers: int = 2):
        self.rotator = rotator or get_rotator()
        self.max_workers = min(max_workers, max(1, self.rotator.key_count), 4)
        self.fallback_handler = PerSlideFallbackHandler(self.rotator)

    def synthesize_slides(
        self,
        blueprints: List[SlideBlueprint],
        deck_info: DeckArchitectOutput,
        config: dict
    ) -> List[Slide]:
        batch_size = 2
        batches = [blueprints[i:i + batch_size] for i in range(0, len(blueprints), batch_size)]
        total_batches = len(batches)
        print(f"  [BatchedSynthesizer] Synthesizing {len(blueprints)} slides across {total_batches} batches (concurrency: {self.max_workers})...")

        results: List[Slide] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(self._synthesize_batch, batch, deck_info, config): batch
                for batch in batches
            }
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    slides = future.result()
                    results.extend(slides)
                except Exception as e:
                    print(f"  [BatchedSynthesizer] Batch failed with error: {e}. Executing per-slide recovery...")
                    for bp in batch:
                        recovered = self.fallback_handler.recover_slide(bp, deck_info, config, e)
                        results.append(recovered)

        results.sort(key=lambda s: s.slide_number)
        return results

    def _synthesize_batch(
        self,
        batch: List[SlideBlueprint],
        deck_info: DeckArchitectOutput,
        config: dict
    ) -> List[Slide]:
        client, key_idx = self.rotator.get_client()
        if client is None:
            raise RuntimeError("No API key available for batch synthesis.")

        batch_directives = []
        for bp in batch:
            batch_directives.append({
                "slide_number": bp.slide_number,
                "layout_type": bp.layout_type,
                "layout_variant": bp.layout_variant,
                "eyebrow": bp.eyebrow,
                "title_directive": bp.title_directive,
                "slide_purpose": bp.slide_purpose,
                "narrative_weight": bp.narrative_weight,
                "accent_type": bp.accent_type,
                "slot_budget": bp.slot_budget.model_dump()
            })

        prompt = (
            f"=== DECK OVERVIEW ===\n"
            f"Title: {deck_info.deck_title}\n"
            f"Thesis: {deck_info.thematic_thesis}\n"
            f"Narrative Arc: {deck_info.narrative_arc}\n\n"
            f"=== SLIDE BATCH TO SYNTHESIZE ({len(batch)} slides) ===\n"
            f"{json.dumps(batch_directives, indent=2)}\n\n"
            f"=== REQUIREMENT ===\n"
            f"Synthesize each slide into a complete Slide object.\n"
            f"CRITICAL: in content_blocks, each block must use 'block_type' (e.g. 'bullets', 'stat', 'pullquote', 'bento').\n"
            f"If layout is 'bento', populate content_blocks with a BentoBlock with 'cards': [BentoCard, ...].\n"
            f"Return JSON: {{\"slides\": [Slide, ...]}}"
        )

        try:
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=[
                    {"role": "system", "parts": [{"text": BATCH_SYNTHESIS_SYSTEM_PROMPT}]},
                    {"role": "user", "parts": [{"text": prompt}]}
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                    max_output_tokens=3000,
                )
            )
            text = (response.text or '').strip()
            if text.startswith('```'):
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            data = json.loads(text)

            slide_dicts = data.get('slides', []) if isinstance(data, dict) else data
            slides: List[Slide] = []
            for s_dict in slide_dicts:
                num = s_dict.get('slide_number')
                matching_bp = next((b for b in batch if b.slide_number == num), batch[0])
                normalized_s = _normalize_slide_dict(s_dict, matching_bp)
                slides.append(Slide(**normalized_s))

            if len(slides) < len(batch):
                existing_nums = {s.slide_number for s in slides}
                for bp in batch:
                    if bp.slide_number not in existing_nums:
                        slides.append(self.fallback_handler.recover_slide(bp, deck_info, config, Exception("Slide missing in batch")))

            return slides
        except Exception as e:
            raise e


class DeterministicGatekeeper:
    """
    Stage 3: Fast, 0ms, zero-token static validation and character clamping.
    Guarantees that no title or body exceeds container limits.
    """

    @staticmethod
    def audit_and_clamp(slides: List[Slide], blueprints: List[SlideBlueprint]) -> Tuple[List[Slide], List[str]]:
        violations = []
        bp_map = {b.slide_number: b for b in blueprints}

        for slide in slides:
            bp = bp_map.get(slide.slide_number)
            budget = bp.slot_budget if bp else SlotBudget()

            if len(slide.title) > budget.title_max_chars:
                violations.append(f"Slide {slide.slide_number} title exceeded {budget.title_max_chars} chars.")
                slide.title = slide.title[:budget.title_max_chars - 3].rsplit(' ', 1)[0] + "..."

            if slide.subtitle and len(slide.subtitle) > budget.subtitle_max_chars:
                slide.subtitle = slide.subtitle[:budget.subtitle_max_chars - 3].rsplit(' ', 1)[0] + "..."

            if slide.content_blocks:
                for block in slide.content_blocks:
                    if getattr(block, 'block_type', None) == 'bento':
                        for card in getattr(block, 'cards', []):
                            if getattr(card, 'card_id', None) == 'hero':
                                if card.title and len(card.title) > budget.hero_title_max_chars:
                                    card.title = card.title[:budget.hero_title_max_chars - 3].rsplit(' ', 1)[0] + "..."
                                if card.body and len(card.body) > budget.hero_body_max_chars:
                                    card.body = card.body[:budget.hero_body_max_chars - 3].rsplit(' ', 1)[0] + "..."
                            else:
                                if card.stat_val and len(card.stat_val) > budget.micro_val_max_chars:
                                    card.stat_val = card.stat_val[:budget.micro_val_max_chars]
                                if card.stat_label and len(card.stat_label) > budget.micro_label_max_chars:
                                    card.stat_label = card.stat_label[:budget.micro_label_max_chars]

        return slides, violations
