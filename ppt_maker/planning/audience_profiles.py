"""
audience_profiles.py — Audience-tailored writing and design guidance.

Each profile is injected into the Planner system prompt as context.
It shapes: vocabulary, evidence depth, visual density, and slide count targets.
"""

from typing import Dict


AUDIENCE_PROFILES: Dict[str, dict] = {

    "investor": {
        "label": "Investors / Angel Investors / VCs",
        "writing_style": (
            "Lead with traction and momentum. Use hard numbers with sources. "
            "Be brutally concise — assume 30 seconds per slide. "
            "No jargon. No buzzwords. Every word must justify being there. "
            "One dominant idea per slide."
        ),
        "evidence_preference": "quantitative",   # stats, metrics, revenue, growth %
        "vocabulary": [
            "TAM", "MRR", "ARR", "burn rate", "runway", "LTV", "CAC",
            "unit economics", "moat", "traction", "conversion rate",
        ],
        "avoid": [
            "synergy", "revolutionary", "disruptive", "best-in-class",
            "world-class", "next-generation", "paradigm shift",
        ],
        "slide_count_target": "8–12",
        "content_density": "low",               # sparse, punchy
        "preferred_blocks": ["stat", "bullets", "comparison"],
        "preferred_layouts": ["cover", "stat", "split", "generic"],
        "speaker_notes_style": (
            "Investor Q&A prep: anticipate tough questions. "
            "Include the assumption behind each claim and the data source."
        ),
    },

    "technical": {
        "label": "Engineers / Developers / Scientists",
        "writing_style": (
            "Be precise and specific. Embrace technical vocabulary. "
            "Show the system design, not just the outcome. "
            "Include failure modes, edge cases, and trade-offs. "
            "Code snippets and architecture diagrams are welcome. "
            "Avoid marketing fluff — this audience will call it out."
        ),
        "evidence_preference": "analytical",    # benchmarks, diffs, code, diagrams
        "vocabulary": [
            "latency", "throughput", "scalability", "architecture", "API",
            "pipeline", "schema", "refactor", "abstraction layer",
            "trade-off", "performance budget", "complexity",
        ],
        "avoid": [
            "solution", "seamless", "intuitive", "user-friendly",
            "leverage (as a verb)", "utilize", "impactful",
        ],
        "slide_count_target": "10–15",
        "content_density": "high",              # dense, detailed
        "preferred_blocks": ["bullets", "steps", "keyvalue", "stat"],
        "preferred_layouts": ["generic", "split", "infographic", "timeline"],
        "speaker_notes_style": (
            "Include implementation details, caveats, and links to docs/source. "
            "Anticipate 'why not X?' questions."
        ),
    },

    "executive": {
        "label": "C-Suite / Senior Leadership",
        "writing_style": (
            "Top-down. State the recommendation or conclusion first. "
            "Then provide only the evidence needed to build confidence. "
            "Executives make decisions — help them decide, don't make them dig for the answer. "
            "Use analogies to make abstract numbers concrete. "
            "No more than 3 key takeaways per slide."
        ),
        "evidence_preference": "strategic",     # business impact, ROI, risk
        "vocabulary": [
            "ROI", "strategic alignment", "risk mitigation", "competitive advantage",
            "market share", "operational efficiency", "stakeholder value",
            "business outcome", "governance", "P&L impact",
        ],
        "avoid": [
            "technical implementation details", "edge cases", "detailed methodology",
            "lengthy lists", "small font sizes", "gratuitous charts",
        ],
        "slide_count_target": "6–10",
        "content_density": "low",
        "preferred_blocks": ["stat", "callout", "comparison", "bullets"],
        "preferred_layouts": ["cover", "stat", "split", "generic"],
        "speaker_notes_style": (
            "Include the 'so what' for every slide. "
            "Frame risk implications and the cost of inaction."
        ),
    },

    "academic": {
        "label": "Researchers / Academic Peers / Conference Audiences",
        "writing_style": (
            "Rigorous and methodologically sound. "
            "Every claim must be attributable (author, year, source). "
            "Define terms before using them. "
            "Show limitations, assumptions, and future work. "
            "Prefer depth over breadth — it's better to thoroughly explain one finding than to skim six."
        ),
        "evidence_preference": "empirical",     # studies, citations, p-values, effect sizes
        "vocabulary": [
            "methodology", "findings", "limitations", "statistical significance",
            "sample size", "control group", "replication", "literature review",
            "hypothesis", "reproducibility", "peer-reviewed",
        ],
        "avoid": [
            "unsubstantiated claims", "anecdotal evidence", "marketing language",
            "superlatives without citation", "'recent studies show' without reference",
        ],
        "slide_count_target": "12–20",
        "content_density": "high",
        "preferred_blocks": ["bullets", "pullquote", "keyvalue", "stat"],
        "preferred_layouts": ["generic", "split", "infographic", "quote"],
        "speaker_notes_style": (
            "Include the full citation for any referenced work. "
            "Note what questions remain open for discussion."
        ),
    },

    "general": {
        "label": "General Public / Mixed Audience",
        "writing_style": (
            "Accessible, engaging, and jargon-free. "
            "Use everyday language and relatable analogies. "
            "Start with a compelling story or surprising fact. "
            "Build to insights — don't lead with conclusions. "
            "One idea per slide, developed fully. "
            "End with something the audience can take away and use immediately."
        ),
        "evidence_preference": "narrative",     # stories, examples, visuals, analogies
        "vocabulary": [
            # No specific vocabulary constraints — just plain language
        ],
        "avoid": [
            "jargon", "acronyms without explanation", "too many statistics",
            "complex charts without annotation", "dense text blocks",
        ],
        "slide_count_target": "8–12",
        "content_density": "low",
        "preferred_blocks": ["bullets", "pullquote", "callout", "stat"],
        "preferred_layouts": ["cover", "split", "quote", "generic", "stat"],
        "speaker_notes_style": (
            "Write as if speaking to a curious friend. "
            "Include the story behind each slide and why it matters to a non-expert."
        ),
    },
}


def get_profile(audience_type: str) -> dict:
    """Return profile dict. Defaults to 'general' if unknown."""
    return AUDIENCE_PROFILES.get(audience_type, AUDIENCE_PROFILES["general"])


def profile_for_prompt(audience_type: str, audience_label: str = '') -> str:
    """
    Return a formatted string injected into the Planner system prompt.
    """
    profile = get_profile(audience_type)
    label = audience_label or profile['label']

    lines = [
        f'AUDIENCE PROFILE: "{audience_type}" — {label}',
        "",
        f"Writing Style:",
        f"  {profile['writing_style']}",
        "",
        f"Evidence preference: {profile['evidence_preference']}",
        f"Target slide count: {profile['slide_count_target']}",
        f"Content density: {profile['content_density']}  "
        f"(low=sparse+punchy, high=dense+detailed)",
    ]

    if profile.get('vocabulary'):
        lines.append(f"Domain vocabulary to use: {', '.join(profile['vocabulary'][:8])}")

    if profile.get('avoid'):
        lines.append(f"Avoid: {', '.join(profile['avoid'][:5])}")

    if profile.get('preferred_blocks'):
        lines.append(f"Preferred content_block types: {', '.join(profile['preferred_blocks'])}")

    lines += [
        "",
        f"Speaker notes style: {profile['speaker_notes_style']}",
    ]

    return "\n".join(lines)
