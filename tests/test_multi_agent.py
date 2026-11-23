"""
tests/test_multi_agent.py — Test suite for Multi-Agent Planning Pipeline and SlidesGo Schemas.
"""

import pytest
from ppt_maker.core.api_keys import APIKeyRotator
from ppt_maker.core.schemas import (
    MasterPlan, Slide, SlideBlueprint, DeckArchitectOutput, SlotBudget,
    BentoBlock, BentoCard, Theme, BulletBlock
)
from ppt_maker.planning.multi_agent.stages import (
    DeckArchitect, BatchedSynthesizer, DeterministicGatekeeper
)
from ppt_maker.planning.multi_agent.fallback import PerSlideFallbackHandler
from ppt_maker.planning.multi_agent.orchestrator import MultiAgentPlanner
from ppt_maker.planning.validator import ContentValidator


def test_api_key_rotator_round_robin():
    """Verify APIKeyRotator round-robin cycling and error advancement."""
    mock_keys = ["key_A", "key_B", "key_C"]
    rotator = APIKeyRotator(mock_keys)
    assert rotator.key_count == 3

    # Consecutive get_client calls cycle keys
    _, idx0 = rotator.get_client()
    _, idx1 = rotator.get_client()
    _, idx2 = rotator.get_client()
    _, idx3 = rotator.get_client()
    assert (idx0, idx1, idx2, idx3) == (0, 1, 2, 0)

    # rotate_on_error advances past failed key
    _, next_idx = rotator.rotate_on_error(failed_index=1)
    assert next_idx == 2


def test_deck_architect_default_blueprint():
    """Verify DeckArchitect produces valid structural blueprints matching target slide counts."""
    architect = DeckArchitect(APIKeyRotator(["mock_key"]))
    blueprint = architect._default_blueprint(slide_count=6, theme='editorial', palette='navy')

    assert isinstance(blueprint, DeckArchitectOutput)
    assert len(blueprint.slides) == 6
    assert blueprint.slides[0].layout_type == 'cover'
    assert blueprint.slides[1].layout_type == 'bento'
    assert blueprint.recommended_theme == 'editorial'
    assert blueprint.recommended_palette == 'navy'


def test_deterministic_gatekeeper_clamping():
    """Verify DeterministicGatekeeper clamps titles and Bento card text at word boundaries."""
    bp = SlideBlueprint(
        slide_number=1,
        layout_type='bento',
        title_directive="Overlong title that exceeds the allowed character budget for the container",
        slot_budget=SlotBudget(title_max_chars=30, hero_body_max_chars=50)
    )

    overlong_card = BentoCard(
        card_id='hero',
        col_span=8,
        title="Valid Short Title",
        body="This is an excessively detailed description that definitely goes way beyond the allocated fifty characters limit."
    )
    bento_block = BentoBlock(variant='bento_8_4', cards=[overlong_card])

    slide = Slide(
        slide_number=1,
        layout_type='bento',
        title="This is an extremely long title that exceeds the slot budget maximum limit",
        content_blocks=[bento_block]
    )

    clamped_slides, violations = DeterministicGatekeeper.audit_and_clamp([slide], [bp])
    assert len(violations) > 0
    # Title must be clamped to <= 30 chars
    assert len(clamped_slides[0].title) <= 30
    assert clamped_slides[0].title.endswith("...")
    # Hero card body must be clamped to <= 50 chars
    hero_card = clamped_slides[0].content_blocks[0].cards[0]
    assert len(hero_card.body) <= 50
    assert hero_card.body.endswith("...")


def test_per_slide_fallback_handler_recovery():
    """Verify PerSlideFallbackHandler returns a valid Slide object without raising exceptions."""
    handler = PerSlideFallbackHandler(APIKeyRotator([]))
    bp = SlideBlueprint(
        slide_number=3,
        layout_type='bento',
        layout_variant='bento_8_4',
        title_directive="Accelerate AI Engineering with Structured Loops",
        eyebrow="ARCHITECTURE",
        slide_purpose="problem_statement"
    )
    deck_info = DeckArchitectOutput(
        deck_title="AI Presentation Agency",
        narrative_arc="problem_solution",
        thematic_thesis="Structured pipelines beat bloated agents.",
        recommended_theme="corporate_clean",
        slides=[bp]
    )

    recovered = handler.recover_slide(bp, deck_info, config={}, error=Exception("Simulated 429 quota exhaustion"))
    assert isinstance(recovered, Slide)
    assert recovered.slide_number == 3
    assert recovered.layout_type == 'bento'
    assert recovered.eyebrow == 'ARCHITECTURE'
    assert len(recovered.content_blocks) > 0
    assert recovered.content_blocks[0].block_type == 'bento'


def test_bento_block_serialization_and_validation():
    """Verify BentoBlock serializes and validates cleanly through ContentValidator."""
    cards = [
        BentoCard(card_id='hero', col_span=8, stat_val='4x', stat_label='Speed', body='Faster execution.'),
        BentoCard(card_id='side_1', col_span=4, stat_val='99%', stat_label='Reliability')
    ]
    bento_block = BentoBlock(variant='bento_8_4', cards=cards)

    slide = Slide(
        slide_number=2,
        layout_type='bento',
        title="Performance Benchmarks",
        content_blocks=[bento_block]
    )

    plan = MasterPlan(
        theme=Theme(structural_class='corporate_clean'),
        slides=[
            Slide(slide_number=1, layout_type='cover', title="Cover Slide"),
            slide
        ]
    )

    # ContentValidator must prune and validate without error
    validated = ContentValidator.validate_and_prune(plan)
    assert len(validated.slides) == 2
    assert validated.slides[1].layout_type == 'bento'
    assert validated.slides[1].content_blocks[0].block_type == 'bento'
    assert len(validated.slides[1].content_blocks[0].cards) == 2

