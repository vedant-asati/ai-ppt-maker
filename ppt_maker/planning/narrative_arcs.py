"""
narrative_arcs.py — Narrative structure blueprints for presentation planning.

Each arc is a dict the Planner injects into the system prompt as a JSON block.
The Planner uses this to decide: slide ordering, purpose labels, layout variety,
and content density distribution.
"""

from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# ARC DEFINITIONS
# Each arc has:
#   description  — one-line summary for the system prompt
#   slide_roles  — ordered list of slide purposes (maps to slide_purpose field)
#   rationale    — why this arc works (injected as context into planner prompt)
#   good_for     — example use cases (shown in config_reference.yaml)
# ─────────────────────────────────────────────────────────────────────────────

NARRATIVE_ARCS: Dict[str, dict] = {

    "problem_solution": {
        "description": "Establish a clear problem, then reveal the solution as the hero moment.",
        "slide_roles": [
            "opening_hook",
            "problem_statement",
            "evidence",            # Data showing the problem is real and costly
            "solution_intro",
            "solution_detail",
            "social_proof",        # Who else solved it this way
            "call_to_action",
        ],
        "extended_roles": [
            "problem_deep_dive",       # Expand on problem with more evidence
            "evidence_2",              # Secondary data from a different angle
            "solution_demo",           # Show it working in practice
            "competitive_landscape",   # How alternatives fall short
            "implementation_steps",    # Practical steps / timeline
            "team_or_credibility",     # Why this team can deliver
            "summary",                 # Recap key points before CTA
        ],
        "rationale": (
            "The most persuasive structure for pitches. "
            "Creates tension early (problem), then releases it with the solution. "
            "Evidence builds credibility before revealing the answer. "
            "End with a specific ask."
        ),
        "good_for": ["investor pitches", "sales decks", "product launches", "grant proposals"],
        "layout_hints": {
            "opening_hook":    "cover",
            "problem_statement": "split",
            "evidence":        "infographic",
            "solution_intro":  "split",
            "solution_detail": "generic",
            "social_proof":    "generic",
            "call_to_action":  "split",
            "problem_deep_dive":    "stat",
            "evidence_2":           "infographic",
            "solution_demo":        "split",
            "competitive_landscape": "generic",
            "implementation_steps":  "timeline",
            "team_or_credibility":   "quote",
            "summary":              "generic",
        },
    },

    "before_after": {
        "description": "Show the painful 'before' state, then contrast with the transformed 'after'.",
        "slide_roles": [
            "opening_hook",
            "before_state",        # Current reality — pain points
            "turning_point",       # The event / insight that changes everything
            "after_state",         # The improved future state
            "how_to_get_there",    # Steps / process
            "call_to_action",
        ],
        "extended_roles": [
            "before_evidence",         # Data proving the before state is bad
            "before_impact",           # Who is affected and how
            "transformation_detail",   # How the change actually happened
            "after_evidence",          # Data proving the after state is real
            "testimonial",             # Who experienced the transformation
            "lessons",                 # What we learned from the journey
            "next_steps",              # What comes next
        ],
        "rationale": (
            "Emotionally resonant structure. "
            "The audience should feel the 'before' pain personally, "
            "making the 'after' state feel like genuine relief, not just marketing."
        ),
        "good_for": ["transformation decks", "case studies", "testimonials", "workshops"],
        "layout_hints": {
            "opening_hook":    "cover",
            "before_state":    "split",
            "turning_point":   "stat",
            "after_state":     "split",
            "how_to_get_there": "timeline",
            "call_to_action":  "generic",
            "before_evidence":       "infographic",
            "before_impact":         "quote",
            "transformation_detail": "generic",
            "after_evidence":        "stat",
            "testimonial":           "quote",
            "lessons":               "generic",
            "next_steps":            "timeline",
        },
    },

    "what_why_how": {
        "description": "Start with the 'what', build credibility with 'why it matters', then deliver the 'how'.",
        "slide_roles": [
            "opening_hook",
            "what_intro",
            "why_it_matters",
            "why_evidence",
            "how_overview",
            "how_step_1",
            "how_step_2",
            "summary",
        ],
        "extended_roles": [
            "what_detail",             # Deeper explanation of the what
            "why_evidence_2",          # More supporting data
            "how_step_3",              # Additional steps
            "how_demo",                # Practical demonstration
            "common_mistakes",         # Pitfalls to avoid
            "advanced_tips",           # Power-user guidance
            "resources",               # Where to learn more
        ],
        "rationale": (
            "Simon Sinek's Golden Circle applied to presentations. "
            "Starting with 'what' orients the audience before 'why' creates desire, "
            "and 'how' satisfies that desire with actionable steps."
        ),
        "good_for": ["educational content", "how-to guides", "technical explanations", "thought leadership"],
        "layout_hints": {
            "opening_hook": "cover",
            "what_intro":   "split",
            "why_it_matters": "stat",
            "why_evidence": "infographic",
            "how_overview": "generic",
            "how_step_1":   "split",
            "how_step_2":   "split",
            "summary":      "generic",
            "what_detail":      "generic",
            "why_evidence_2":   "infographic",
            "how_step_3":       "timeline",
            "how_demo":         "split",
            "common_mistakes":  "quote",
            "advanced_tips":    "generic",
            "resources":        "stat",
        },
    },

    "journey": {
        "description": "Walk the audience through a chronological or sequential story.",
        "slide_roles": [
            "opening_hook",
            "beginning",           # Where the story starts
            "challenge",           # First obstacle
            "effort",              # The work/struggle
            "breakthrough",        # Key discovery or turning point
            "outcome",             # Results achieved
            "lessons_learned",
            "call_to_action",
        ],
        "extended_roles": [
            "context",                 # Background setting the stage
            "challenge_2",             # Second or deeper obstacle
            "mentor_or_ally",          # Who helped along the way
            "setback",                 # A moment of doubt or failure
            "outcome_detail",          # Deeper results / impact
            "ripple_effects",          # What changed because of the outcome
            "vision",                  # Where the journey goes next
        ],
        "rationale": (
            "Narrative arc with emotional peaks. "
            "The journey structure makes abstract progress tangible. "
            "Best used when the presenter has a real story to tell "
            "(company history, research journey, personal experience)."
        ),
        "good_for": ["company stories", "research presentations", "retrospectives", "keynotes"],
        "layout_hints": {
            "opening_hook":   "cover",
            "beginning":      "split",
            "challenge":      "quote",
            "effort":         "timeline",
            "breakthrough":   "stat",
            "outcome":        "infographic",
            "lessons_learned": "generic",
            "call_to_action": "split",
            "context":          "generic",
            "challenge_2":      "split",
            "mentor_or_ally":   "quote",
            "setback":          "stat",
            "outcome_detail":   "infographic",
            "ripple_effects":   "generic",
            "vision":           "split",
        },
    },

    "contrast": {
        "description": "Present two competing options and make a clear case for one.",
        "slide_roles": [
            "opening_hook",
            "framing",             # Set up the two options
            "option_a_intro",
            "option_a_evidence",
            "option_b_intro",
            "option_b_evidence",
            "comparison",          # Side-by-side or criteria table
            "recommendation",
            "call_to_action",
        ],
        "extended_roles": [
            "option_a_detail",         # Deeper dive into option A
            "option_b_detail",         # Deeper dive into option B
            "criteria_breakdown",      # Evaluation framework
            "risk_analysis",           # Risks of each option
            "implementation_plan",     # How to execute the recommendation
            "stakeholder_impact",      # Who benefits from the choice
        ],
        "rationale": (
            "Creates intellectual tension by fairly presenting two sides, "
            "then building a persuasive case for the recommended option. "
            "Audiences respect balanced treatment before the recommendation lands."
        ),
        "good_for": ["technology comparisons", "strategic decisions", "debate-style content", "vendor evaluations"],
        "layout_hints": {
            "opening_hook":   "cover",
            "framing":        "generic",
            "option_a_intro": "split",
            "option_a_evidence": "infographic",
            "option_b_intro": "split",
            "option_b_evidence": "infographic",
            "comparison":     "generic",
            "recommendation": "stat",
            "call_to_action": "split",
            "option_a_detail":      "generic",
            "option_b_detail":      "generic",
            "criteria_breakdown":   "timeline",
            "risk_analysis":        "quote",
            "implementation_plan":  "timeline",
            "stakeholder_impact":   "stat",
        },
    },

    "inverted_pyramid": {
        "description": "Lead with the conclusion, then support it with increasing detail.",
        "slide_roles": [
            "opening_hook",
            "thesis",              # The main conclusion stated upfront
            "key_evidence_1",
            "key_evidence_2",
            "key_evidence_3",
            "supporting_context",
            "implications",
            "call_to_action",
        ],
        "extended_roles": [
            "thesis_expansion",        # Why the thesis matters now
            "key_evidence_4",          # Additional evidence
            "counterargument",         # Addressing the obvious objection
            "expert_voice",            # Quote from authority
            "real_world_example",      # Case study or concrete instance
            "methodology",             # How the evidence was gathered
            "next_steps",              # Actionable next steps
        ],
        "rationale": (
            "Borrowed from journalism. Executives and busy audiences love this — "
            "they hear the answer first and can leave at any point with the key message. "
            "Each slide reinforces and deepens the opening thesis."
        ),
        "good_for": ["executive briefings", "board presentations", "research summaries", "news-style reporting"],
        "layout_hints": {
            "opening_hook":    "cover",
            "thesis":          "stat",
            "key_evidence_1":  "split",
            "key_evidence_2":  "split",
            "key_evidence_3":  "infographic",
            "supporting_context": "generic",
            "implications":    "generic",
            "call_to_action":  "split",
            "thesis_expansion":    "generic",
            "key_evidence_4":      "infographic",
            "counterargument":     "quote",
            "expert_voice":        "quote",
            "real_world_example":  "split",
            "methodology":         "timeline",
            "next_steps":          "generic",
        },
    },

    "showcase": {
        "description": "Feature the product, work, or idea center-stage with stunning visuals.",
        "slide_roles": [
            "opening_hook",
            "overview",
            "feature_1",
            "feature_2",
            "feature_3",
            "in_action",           # Demo / real-world use
            "testimonial",
            "call_to_action",
        ],
        "extended_roles": [
            "feature_4",               # Additional feature
            "feature_5",               # Additional feature
            "behind_the_scenes",       # How it was built / designed
            "impact_stats",            # Results / usage numbers
            "community",               # User community or ecosystem
            "roadmap",                 # What's coming next
            "pricing_or_access",       # How to get started
        ],
        "rationale": (
            "Portfolio and product showcase structure. "
            "Lets the work speak for itself. "
            "Each feature slide should be visually distinct — "
            "avoid repeating the same layout back-to-back."
        ),
        "good_for": ["portfolio decks", "product demos", "design presentations", "award submissions"],
        "layout_hints": {
            "opening_hook": "cover",
            "overview":     "generic",
            "feature_1":    "split",
            "feature_2":    "split",
            "feature_3":    "infographic",
            "in_action":    "split",
            "testimonial":  "quote",
            "call_to_action": "stat",
            "feature_4":          "split",
            "feature_5":          "split",
            "behind_the_scenes":  "timeline",
            "impact_stats":       "stat",
            "community":          "quote",
            "roadmap":            "timeline",
            "pricing_or_access":  "generic",
        },
    },
}


def get_arc(arc_name: str) -> dict:
    """Return the arc dict, defaulting to problem_solution if name unknown."""
    return NARRATIVE_ARCS.get(arc_name, NARRATIVE_ARCS["problem_solution"])


def arc_for_prompt(arc_name: str, slide_count: int = None) -> str:
    """
    Return a formatted string injected into the Planner system prompt.
    Describes the slide order and each role's purpose.

    When slide_count > len(base roles), extended_roles are spliced in
    before the final role (which is always CTA/summary).
    """
    arc = get_arc(arc_name)
    base_roles = list(arc["slide_roles"])

    # Scale roles for longer decks
    if slide_count and slide_count > len(base_roles) and "extended_roles" in arc:
        extra_needed = slide_count - len(base_roles)
        extended = arc["extended_roles"][:extra_needed]
        # Insert extended roles before the last base role (CTA/summary stays last)
        roles = base_roles[:-1] + extended + [base_roles[-1]]
    else:
        roles = base_roles

    lines = [
        f'NARRATIVE STRUCTURE: "{arc_name}"',
        f'Description: {arc["description"]}',
        "",
        f"Planned slide sequence ({len(roles)} roles for your deck):",
    ]
    for i, role in enumerate(roles, 1):
        hint = arc.get("layout_hints", {}).get(role, "any")
        lines.append(f"  {i}. {role}  →  layout hint: {hint}")

    lines += [
        "",
        f"Rationale: {arc['rationale']}",
        "",
        "IMPORTANT: Adapt this sequence to the actual content.",
        "If the source material doesn't support a role (e.g. no testimonials), skip it.",
        "Do NOT pad with empty content to fill all roles.",
    ]
    return "\n".join(lines)
