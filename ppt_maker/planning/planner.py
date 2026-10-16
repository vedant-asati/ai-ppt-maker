import os
import sys
import json
import time
import re
from google import genai
from google.genai import types
try:
    from ppt_maker.core.schemas import MasterPlan
except ImportError:
    from schemas import MasterPlan

# ─────────────────────────────────────────────────────────────────────────────
# System prompt — premium content quality rules
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_CORE = """\
You are an elite Presentation Design Agency composed of three expert roles working in harmony:
  • Narrative Architect: structures the story, determines slide purposes, and writes all copy.
  • Art Director: selects layouts, visual hierarchy, and image direction.
  • CSS Themer: sets the color palette, structural class, and design tokens.

Your sole output is a single, valid JSON object. No markdown, no explanation, no extra text.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I. CONTENT QUALITY RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Apply ALL of these rules. Violation of any rule is a failure.

1.  ONE IDEA PER SLIDE. Each slide makes exactly one clear point. If you have two ideas, make two slides.
2.  LEAD WITH THE INSIGHT. Start the title with the key takeaway — not a category label.
    BAD:  "Market Analysis"
    GOOD: "The Market Grew 3x in 24 Months — Timing Is Everything"
3.  ACTIVE TITLES. Verbs in titles create energy.
    BAD:  "Benefits of the Solution"
    GOOD: "Cut Processing Time by 85% With One Integration"
4.  EVIDENCE FIRST. When you have a statistic, put it on the slide — not vague language.
    BAD:  "Growth has been significant."
    GOOD: "Monthly active users grew from 12k to 140k in 8 months."
5.  BULLETS ARE A LAST RESORT. If the content fits in a StatBlock, PullQuoteBlock, ComparisonBlock,
    or StepBlock — use those. Flat bullet lists signal lazy design.
6.  MAX 5 BULLETS. Never exceed 5 items in a BulletBlock. If you have 6+, split the slide.
7.  BULLETS ARE SCANNABLE. Each bullet: one idea, one clause. No semicolons. Max 120 chars.
8.  NO FILLER. Delete these phrases from your output: "In order to", "It is important to note",
    "As mentioned", "In conclusion", "To summarize", "Going forward", "Leverage", "Synergy",
    "Utilize", "Paradigm shift", "At the end of the day", "Moving forward", "Best-in-class".
9.  NO VAGUE CLAIMS. Every claim needs evidence. "We are the best" → remove or cite.
    "We grew fast" → add the number. "Our solution is efficient" → define what efficiency means.
10. SPECIFIC NOUNS. Name the product, person, company, technology. Avoid "the solution", "the tool",
    "the platform". Use the real name from the source material.
11. VARY CONTENT DENSITY. Not every slide should be dense with text.
    Plan at least 1–2 "breathing room" slides (narrative_weight = "light") with a single powerful
    number, quote, or statement. These create visual rhythm in the deck.
12. EYEBROW LABELS. Use the `eyebrow` field to give context to the slide's role.
    Examples: "Problem", "Key Insight", "Our Approach", "Phase 2", "The Result", "Next Steps"
13. SPEAKER NOTES. Write 3–5 sentences per slide in the speaker's natural voice —
    not a summary of what's on screen, but what the presenter should ADD verbally.
    Include the story behind the data, the emotional beat, or the question to prompt.
14. LAYOUT VARIETY. {{LAYOUT_VARIETY_RULE}}
15. IMAGE PROMPTS. When requires_image=true, write a SPECIFIC, DETAILED image prompt with ALL 6 elements:
    a) SUBJECT: what is depicted — concrete, not abstract. E.g. "a farmer looking at a smartphone".
    b) STYLE: "editorial illustration" | "watercolor" | "flat design" | "photorealistic"
    c) PALETTE: specific colours matching the theme mood. E.g. "warm amber and forest green tones".
    d) COMPOSITION: For panel/generic/infographic layouts → "portrait composition, vertical emphasis, center of frame clear."
                    For split layout → "landscape, left-half clear for text overlay."
                    For cover → "landscape, left-half clear for text overlay, dramatic lighting."
    e) DETAIL: "fine linework" | "bold shapes" | "textured brush strokes" | "deep depth of field"
    f) EXCLUSIONS: end with "No text, logos, watermarks, or UI elements."
    BAD:  "Abstract background."
    GOOD: "Editorial illustration of a government official distributing ration cards to rural families,
           warm terracotta and saffron tones, fine linework, portrait composition for right-side panel,
           vertical emphasis, subject in center of frame. No text, logos, or watermarks."
16. LAYOUT SELECTION LOGIC:
    • cover:       Title slide only. First slide always.
    • split:       Text on one side, image on other. Best for concepts with a visual metaphor.
    • infographic: Data-heavy slide with 3 key stats or a diagram.
    • generic:     Full-width text. Use for process steps, dense evidence, conclusions.
    • quote:       Full-slide pull quote. Reserve for a powerful statement.
    • stat:        One hero number with context. Maximum impact.
    • timeline:    Ordered sequence of 3–5 steps or time periods.
17. PALETTE SELECTION. When using dark_neon, gradient_flow, editorial, or aurora themes,
    ALWAYS include a `palette` field in the theme object with a named palette.
    For dark_neon: cyber_cyan | neon_magenta | electric_blue | acid_lime | solar_orange
    For gradient_flow: violet_sunset | ocean_depth | forest_dusk | ember_night
    For editorial: navy | crimson | forest | terracotta | slate | mustard | parchment
    For aurora: cosmic | arctic | wildfire | bio
    Note: `parchment` is a warm Indian heritage palette (rust primary on cream background).
18. IMAGE ROLES. Set image_role per layout to ensure the right visual treatment:
    • 'panel':       For generic, infographic, timeline layouts — portrait image in right 37%.
    • 'supporting':  For split layout — image fills the right half of a 50/50 split.
    • 'background':  For cover layout — full-bleed image behind text.
    • 'decorative':  Subtle low-opacity texture layer. Use sparingly.
19. ENGAGEMENT PROMPT. For content slides (not cover/stat/quote), add an optional
    "engagement_prompt" — a single reflective question to ask the audience. Max 120 chars.
    It should connect the slide content to the viewer's personal experience.
    EXAMPLE: "When did you last make a decision based on incomplete information?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
II. JSON OUTPUT SCHEMA (EXACT FORMAT REQUIRED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "theme": {
    "css_variables": {"--bg": "#...", "--primary": "#...", "--text": "#...", "--text-secondary": "#..."},
    "structural_class": "minimalist|glassmorphism|neo_brutalism|corporate_clean|dark_neon|gradient_flow|editorial|aurora",
    "palette": "optional_palette_name_for_dark_neon_gradient_flow_editorial_aurora"
  },
  "slides": [
    {
      "slide_number": 1,
      "layout_type": "cover|split|infographic|generic|quote|stat|timeline",
      "layout_variant": null,
      "title": "Verb-led, specific, max 8 words",
      "subtitle": "Optional. Max 120 chars.",
      "eyebrow": "Short category label. e.g. 'Problem', 'Key Insight'. Max 30 chars.",
      "slide_purpose": "opening_hook|problem_statement|evidence|solution_intro|call_to_action|etc",
      "narrative_weight": "light|standard|heavy",
      "content_blocks": [
        {
          "block_type": "bullets",
          "items": ["Specific, scannable point. Max 120 chars.", "Another point."]
        }
      ],
      "content_bullets": [],
      "speaker_notes": "3–5 sentences in the presenter's voice. Not a summary of the slide — adds context and emotion.",
      "requires_image": true,
      "image_prompt": "SPECIFIC prompt with: subject, style, palette, composition, detail level, exclusions.",
      "image_role": "panel (for generic/infographic/timeline) | supporting (for split) | background (for cover) | decorative",
      "engagement_prompt": "Optional: one reflective question for the audience. Max 120 chars. Null for cover/stat/quote."
    }
  ]
}

content_block types:
  {"block_type": "bullets", "items": ["..."]}
  {"block_type": "stat", "value": "400%", "label": "ROI Improvement", "context": "vs. industry average of 120%"}
  {"block_type": "pullquote", "quote": "The quote text", "attribution": "— Name, Title"}
  {"block_type": "comparison", "left_label": "Before", "left_items": ["..."], "right_label": "After", "right_items": ["..."]}
  {"block_type": "steps", "steps": ["Step text..."], "step_labels": ["Phase 1"]}
  {"block_type": "callout", "text": "The highlighted text.", "callout_type": "insight|warning|tip|fact"}
  {"block_type": "keyvalue", "pairs": [{"key": "Accuracy", "value": "99.7%"}, {"key": "Latency", "value": "<10ms"}]}
"""

RETRYABLE_ERRORS = (
    "429", "quota", "resource_exhausted",
    "extra data", "json", "jsondecode",
    "validationerror", "validation error",
)


def _extract_json(text: str) -> str:
    """Robustly extract a JSON object from a model response."""
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return text.strip()


def _get(config, *keys, default=None):
    """Unified config accessor for both AppConfig and raw dict."""
    obj = config
    for key in keys:
        if hasattr(obj, key):
            obj = getattr(obj, key)
        elif isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return default
        if obj is None:
            return default
    return obj if obj is not None else default


def _layout_variety_rule(n: int) -> str:
    """Return a scale-aware layout variety rule for the system prompt."""
    if n <= 7:
        return (
            "No 3 consecutive slides with the same layout_type. "
            "Use at least 3 different layout types. "
            "Mix: split, generic, infographic, stat, quote, timeline."
        )
    elif n <= 12:
        return (
            "No 2 consecutive slides with the same layout_type. "
            "Use at least 5 different layout types across the deck. "
            "Include at least 2 slides with narrative_weight='light' (quote or stat) for visual breathing room. "
            "Mix: split, generic, infographic, stat, quote, timeline."
        )
    else:
        return (
            "No 2 consecutive slides with the same layout_type. "
            "Use at least 6 different layout types across the deck. "
            "Include at least 3 slides with narrative_weight='light' for visual breathing room. "
            "Group slides into 3-4 thematic sections using consistent eyebrow labels "
            "(e.g., 'Context', 'Deep Dive', 'Impact', 'Next Steps'). "
            "Each section should start with a different layout type than the previous section ended with."
        )


def _layout_rhythm_guide(n: int) -> str:
    """Generate a per-position layout suggestion guide for the prompt."""
    if n <= 7:
        return ""  # Short decks don't need position guidance

    # Build rhythm pattern: cover → exposition → impact → dive → breathing → synthesis → CTA
    guide = [
        "LAYOUT RHYTHM GUIDE (suggested — adapt to your content):",
        f"  For a {n}-slide deck, follow this visual rhythm:",
        "",
    ]

    # Define the pattern segments
    positions = ["cover"]  # Pos 1 always cover

    # Fill remaining positions with a rhythm pattern
    content_pool = ["split", "generic", "infographic", "timeline"]
    impact_pool = ["stat", "quote"]

    i = 1  # Already have cover at pos 0
    while i < n:
        remaining = n - i
        if remaining <= 1:
            positions.append("generic or split (conclusion / CTA)")
            i += 1
        elif remaining == 2:
            positions.append("stat or quote (impact moment — narrative_weight=light)")
            positions.append("generic or split (call to action)")
            i += 2
        else:
            # Pattern: 2-3 content slides → 1 breathing room slide
            # Content block
            block_size = min(3, remaining - 1)  # Leave room for breathing room
            for j in range(block_size):
                c_idx = (i + j) % len(content_pool)
                alt_idx = (c_idx + 1) % len(content_pool)
                positions.append(f"{content_pool[c_idx]} or {content_pool[alt_idx]}")
            i += block_size

            if i < n - 1:  # Not the last slide
                b_idx = ((i // 4) % len(impact_pool))
                positions.append(f"{impact_pool[b_idx]} (breathing room — narrative_weight=light)")
                i += 1

    for pos_idx, desc in enumerate(positions[:n]):
        guide.append(f"  Slide {pos_idx + 1}: {desc}")

    guide.append("")
    guide.append("  IMPORTANT: This is a GUIDE, not a rigid template. Adapt to content needs.")
    return "\n".join(guide)


class Planner:
    def __init__(self):
        try:
            from ppt_maker.core.api_keys import get_api_keys, get_client
        except ImportError:
            from api_keys import get_api_keys, get_client
        self._keys = get_api_keys()
        if not self._keys:
            print("Error: No GEMINI_API_KEY* environment variables set. Cannot run Master Planner.")
            sys.exit(1)
        self._key_idx = 0
        self.client, self._key_idx = get_client(0)
        if len(self._keys) > 1:
            print(f"  [Planner] {len(self._keys)} API keys available — will rotate on rate limit.")

    def generate_master_plan(self, config) -> MasterPlan:
        print("Master Planner: Analyzing configuration and generating presentation blueprint...")

        # ── Extract config values ─────────────────────────────────────────
        source_text   = (_get(config, 'source_text') or '').strip()
        source_file   = (_get(config, 'source_file') or '').strip()

        audience      = _get(config, 'presentation_goals', 'audience', default='General')
        duration      = _get(config, 'presentation_goals', 'duration_minutes', default=10)
        slide_count   = _get(config, 'presentation_goals', 'slide_count', default=None)
        tone          = _get(config, 'presentation_goals', 'tone', default='professional')
        language      = _get(config, 'presentation_goals', 'language', default='English')
        cta           = _get(config, 'presentation_goals', 'call_to_action', default=None)
        narrative_arc = _get(config, 'presentation_goals', 'narrative_arc', default=None)
        audience_type = _get(config, 'presentation_goals', 'audience_type', default=None)

        theme_style   = _get(config, 'design_preferences', 'theme_style', default='corporate_clean')
        primary_color = _get(config, 'design_preferences', 'primary_color', default='')
        palette       = _get(config, 'design_preferences', 'palette', default=None)
        color_mode    = _get(config, 'design_preferences', 'color_mode', default='auto')
        art_style     = _get(config, 'image_preferences', 'art_style', default='professional illustration')

        # ── Handle source_file upload ─────────────────────────────────────
        uploaded_file = None
        if source_file and os.path.exists(source_file):
            ext = os.path.splitext(source_file)[1].lower()
            if ext in ['.pdf', '.mp3', '.mp4', '.jpg', '.jpeg', '.png']:
                print(f"  Uploading multi-modal source file: {source_file}")
                try:
                    uploaded_file = self.client.files.upload(file=source_file)
                except Exception as e:
                    print(f"  [Warning] Multi-modal upload failed: {e}. Proceeding without file.")
            else:
                try:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        source_text += "\n\n--- CONTENT FROM FILE ---\n\n" + f.read()
                except Exception as e:
                    print(f"  [Warning] Could not read source_file '{source_file}': {e}")

        # ── Source analysis ───────────────────────────────────────────────
        source_analysis_block = ''
        if source_text and len(source_text) > 50:
            try:
                try:
                    from ppt_maker.planning.source_analyzer import analyze_source
                except ImportError:
                    from source_analyzer import analyze_source
                source_analysis_block = analyze_source(source_text) or ''
                if source_analysis_block:
                    print("  [Planner] Source pre-analysis complete.")
            except ImportError:
                pass

        # ── Narrative arc context ─────────────────────────────────────────
        arc_block = ''
        if narrative_arc:
            try:
                try:
                    from ppt_maker.planning.narrative_arcs import arc_for_prompt
                except ImportError:
                    from narrative_arcs import arc_for_prompt
                arc_block = arc_for_prompt(narrative_arc, slide_count=slide_count)
                print(f"  [Planner] Narrative arc: {narrative_arc}")
            except ImportError:
                pass

        # ── Audience profile context ──────────────────────────────────────
        profile_block = ''
        if audience_type:
            try:
                try:
                    from ppt_maker.planning.audience_profiles import profile_for_prompt
                except ImportError:
                    from audience_profiles import profile_for_prompt
                profile_block = profile_for_prompt(audience_type, audience)
                print(f"  [Planner] Audience profile: {audience_type}")
            except ImportError:
                pass

        # ── Build user prompt ─────────────────────────────────────────────
        target_slides = slide_count or max(6, duration)
        slide_count_instruction = (
            f"Exactly {slide_count} slides." if slide_count
            else f"~{target_slides} slides (1 per minute, min 6)."
        )
        print(f"  [Planner] Target: {target_slides} slides")

        prompt_parts = [
            "=== USER CONFIGURATION ===",
            f"Audience:          {audience}",
            f"Slide Count:       {slide_count_instruction}",
            f"Duration:          {duration} minutes",
            f"Tone:              {tone}",
            f"Language:          {language}",
            f"Theme Style:       {theme_style}",
            f"Primary Color:     {primary_color or 'choose based on theme'}",
            f"Color Mode:        {color_mode}",
            f"Art Style:         {art_style}",
        ]
        if palette:
            prompt_parts.append(f"Palette Override:  {palette}")
        if cta:
            prompt_parts.append(f"Call to Action:    {cta}")

        prompt = "\n".join(prompt_parts)

        # Inject pre-analysis (with source override if user specified count)
        if source_analysis_block:
            if slide_count:
                # Don't let source analyzer's estimate override user's explicit count
                import re as _re
                source_analysis_block = _re.sub(
                    r'Suggested slide count: \d+',
                    f'Suggested slide count: {slide_count} (user-specified — follow this exactly)',
                    source_analysis_block
                )
            prompt += f"\n\n=== SOURCE PRE-ANALYSIS ===\n{source_analysis_block}"

        # Inject layout rhythm guide for 8+ slide decks
        rhythm_guide = _layout_rhythm_guide(target_slides)
        if rhythm_guide:
            prompt += f"\n\n=== {rhythm_guide}"

        # Inject audience profile
        if profile_block:
            prompt += f"\n\n=== {profile_block}"

        # Inject narrative arc
        if arc_block:
            prompt += f"\n\n=== {arc_block}"

        # Source text
        if source_text:
            # Truncate very long source texts to stay within context window
            MAX_SOURCE_CHARS = 18000
            if len(source_text) > MAX_SOURCE_CHARS:
                source_text = source_text[:MAX_SOURCE_CHARS]
                prompt += f"\n\n=== SOURCE MATERIAL (truncated to {MAX_SOURCE_CHARS} chars) ===\n{source_text}"
                print(f"  [Planner] Source text truncated to {MAX_SOURCE_CHARS} chars.")
            else:
                prompt += f"\n\n=== SOURCE MATERIAL ===\n{source_text}"

        contents = [prompt]
        if uploaded_file:
            contents.append(uploaded_file)

        # ── Retry loop ────────────────────────────────────────────────────
        # Substitute Rule 14 placeholder with scale-aware version
        system_prompt = _SYSTEM_CORE.replace(
            '{{LAYOUT_VARIETY_RULE}}',
            _layout_variety_rule(target_slides)
        )

        # Dynamic token budget — 15 slides need more output space
        max_tokens = 12000 if target_slides <= 8 else 20000

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.5,
                        max_output_tokens=max_tokens,
                    )
                )

                if response.usage_metadata:
                    print(
                        f"  Tokens: {response.usage_metadata.total_token_count} "
                        f"(in={response.usage_metadata.prompt_token_count}, "
                        f"out={response.usage_metadata.candidates_token_count})"
                    )

                if response.candidates and response.candidates[0].finish_reason.name == 'SAFETY':
                    raise ValueError(
                        "Response blocked by safety filters. Try rephrasing your source material."
                    )

                raw_text    = _extract_json(response.text)
                plan_dict   = json.loads(raw_text)
                master_plan = MasterPlan(**plan_dict)
                print(f"  Master Planner: Generated {len(master_plan.slides)} slides.")

                if uploaded_file:
                    try:
                        self.client.files.delete(name=uploaded_file.name)
                    except Exception:
                        pass

                return master_plan

            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = any(token in error_msg for token in RETRYABLE_ERRORS)

                # On 429, try rotating to next API key before waiting
                if ('429' in error_msg or 'resource_exhausted' in error_msg) and len(self._keys) > 1:
                    old_idx = self._key_idx
                    self._key_idx = (self._key_idx + 1) % len(self._keys)
                    try:
                        from ppt_maker.core.api_keys import get_client
                    except ImportError:
                        from api_keys import get_client
                    self.client, self._key_idx = get_client(self._key_idx)
                    print(f"  [Planner] Key #{old_idx+1} rate-limited → switching to key #{self._key_idx+1}")
                    continue  # Retry immediately with new key

                if is_retryable and attempt < max_retries - 1:
                    wait_time = 2 ** attempt * 15  # 15s, 30s, 60s
                    print(
                        f"  [Planner] Retryable error (attempt {attempt + 1}/{max_retries}): "
                        f"{str(e)[:120]}"
                    )
                    print(f"            Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    if uploaded_file:
                        try:
                            self.client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass
                    print(f"  [Planner Error] Failed after {attempt + 1} attempt(s): {e}")
                    sys.exit(1)

        print("Error: Max retries exceeded for Gemini API.")
        sys.exit(1)
