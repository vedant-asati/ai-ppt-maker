import os
import sys
import re
import time
import threading
from collections import deque
from google import genai
from PIL import Image, ImageDraw, ImageFont
from rich.progress import track
from rich import print as rprint
try:
    from ppt_maker.core.schemas import MasterPlan
    from ppt_maker.imaging.image_cache import ImageCache
    from ppt_maker.design.gradient_generator import GradientGenerator
except ImportError:
    from schemas import MasterPlan
    from image_cache import ImageCache
    from gradient_generator import GradientGenerator


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiter — token bucket
# ─────────────────────────────────────────────────────────────────────────────

class _RateLimiter:
    """
    Token-bucket rate limiter.
    Tracks API call timestamps and blocks when the per-minute quota is reached.
    """

    def __init__(self, max_per_minute: int = 5, max_wait_seconds: int = 120):
        self.max_per_minute   = max_per_minute
        self.max_wait_seconds = max_wait_seconds
        self._timestamps: deque = deque()   # timestamps of recent API calls
        self._lock = threading.Lock()
        self._backoff = 0   # extra seconds added after 429s

    def wait_if_needed(self) -> bool:
        """Block until a request slot is available. Returns False if timeout exceeded."""
        with self._lock:
            now = time.time()
            # Drop timestamps older than 60 seconds
            while self._timestamps and now - self._timestamps[0] > 60:
                self._timestamps.popleft()

            if len(self._timestamps) < self.max_per_minute and self._backoff == 0:
                self._timestamps.append(now)
                return True

            # Calculate wait time
            if self._timestamps:
                wait = 60 - (now - self._timestamps[0]) + self._backoff
            else:
                wait = self._backoff

            if wait > self.max_wait_seconds:
                print(f"  [RateLimit] Wait time {wait:.0f}s exceeds max {self.max_wait_seconds}s — skipping.")
                return False

            if wait > 0:
                print(f"  [RateLimit] Quota reached. Waiting {wait:.0f}s...")
                time.sleep(wait)

            self._backoff = 0
            self._timestamps.append(time.time())
            return True

    def record_429(self, retry_delay_s: int = 30):
        """Record a 429 response — increases backoff."""
        with self._lock:
            self._backoff = min(retry_delay_s * 2, self.max_wait_seconds)

    def record_success(self):
        with self._lock:
            self._backoff = max(0, self._backoff - 5)


# Image generation priority by layout type (P0 = highest)
_PRIORITY = {
    'cover':       0,   # P0: always generate — most impactful
    'split':       0,   # P0: image is central to the layout
    'stat':        1,   # P1: supporting image
    'quote':       1,   # P1: background behind quote
    'timeline':    2,   # P2: background
    'generic':     2,   # P2: optional background
    'infographic': 3,   # P3: rarely used — skip to fallback if rate limited
}


class ImageGenerator:
    def __init__(self, assets_dir: str = 'assets', images_dir: str = None):
        self.assets_dir = assets_dir
        self.images_dir = images_dir  # Optional user-supplied images directory
        os.makedirs(self.assets_dir, exist_ok=True)

        try:
            from ppt_maker.core.api_keys import get_api_keys, get_client
        except ImportError:
            from api_keys import get_api_keys, get_client
        self._keys = get_api_keys()
        self.has_api = bool(self._keys)
        self._key_idx = 0
        effective_rpm = max(5, 5 * len(self._keys))
        self._rate_limiter = _RateLimiter(max_per_minute=effective_rpm, max_wait_seconds=120)
        self._gradient_gen = GradientGenerator()

        if self.images_dir:
            if os.path.isdir(self.images_dir):
                imgs = [f for f in os.listdir(self.images_dir)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                rprint(f"ImageGenerator: Found {len(imgs)} images in --images-dir '{self.images_dir}'")
            else:
                rprint(f"ImageGenerator: [Warning] --images-dir '{self.images_dir}' does not exist.")
                self.images_dir = None

        if self.has_api:
            self.client, self._key_idx = get_client(0)
            self.api_key = self._keys[0]
        else:
            rprint("ImageGenerator: No API key — operating in offline gradient mode.")

    def generate_all(
        self,
        master_plan: MasterPlan,
        config=None,
        force: bool = False,
    ) -> dict:
        """
        Generate all required slide images.

        Returns image_manifest: dict[slide_number -> {path, status, role}]
        """
        rprint("ImageGenerator: Processing image requirements...")

        config = config or {}
        # Support both AppConfig and raw dict
        try:
            art_style     = config.image_preferences.art_style
            theme_style   = config.design_preferences.theme_style
            primary_color = config.design_preferences.primary_color or ''
            audience      = config.presentation_goals.audience
        except AttributeError:
            img_prefs     = (config.get('image_preferences') or {})
            design_prefs  = (config.get('design_preferences') or {})
            goals         = (config.get('presentation_goals') or {})
            art_style     = img_prefs.get('art_style', '')
            theme_style   = design_prefs.get('theme_style', 'corporate_clean')
            primary_color = design_prefs.get('primary_color', '')
            audience      = goals.get('audience', '')

        current_theme  = master_plan.theme.structural_class
        total_slides   = len(master_plan.slides)
        image_manifest = {}
        prompts_export = []

        # Warn if theme changed since last run
        cache = ImageCache(self.assets_dir)
        if cache.theme_changed(current_theme) and not force:
            rprint(
                f"  [Cache] Theme changed to '{current_theme}' — "
                f"images from previous theme may be stale. Use --force-images to regenerate."
            )

        # Sort slides by generation priority (P0 first)
        slides_by_priority = sorted(
            master_plan.slides,
            key=lambda s: _PRIORITY.get(s.layout_type, 2)
        )

        # Track stats for summary
        stats = {'api': 0, 'cache': 0, 'fallback': 0, 'skip': 0, 'matched': 0}

        # ── Smart matching: analyze user images and assign to slides ──────
        smart_match = {}  # slide_number → ImageAssignment
        if self.images_dir:
            try:
                try:
                    from ppt_maker.imaging.image_matcher import ImageMatcher
                except ImportError:
                    from image_matcher import ImageMatcher
                matcher = ImageMatcher(api_key=self.api_key, cache_dir=self.assets_dir)
                match_result = matcher.match(self.images_dir, master_plan.slides)
                smart_match = match_result.assignments

                # Upgrade requires_image=False slides if high confidence match
                for sn, assignment in smart_match.items():
                    slide = next((s for s in master_plan.slides if s.slide_number == sn), None)
                    if slide and not slide.requires_image and assignment.confidence >= 0.8:
                        slide.requires_image = True
                        slide.image_role = slide.image_role or 'background'
                        rprint(f"  [Upgrade] Slide {sn}: upgraded to use image "
                               f"(conf={assignment.confidence:.0%})")
            except Exception as e:
                rprint(f"  [ImageMatcher] Error: {e} — continuing without smart matching.")
                smart_match = {}

        for slide in track(slides_by_priority, description="Generating Images..."):
            if not slide.requires_image:
                continue

            out_path   = os.path.join(self.assets_dir, f"slide_{slide.slide_number}.png")
            image_role = (getattr(slide, 'image_role', None) or 'background')
            raw_prompt = (slide.image_prompt or '').strip() or "Abstract background"
            priority   = _PRIORITY.get(slide.layout_type, 2)

            # Build prompt export entry
            rich_entry = self._build_prompt_entry(
                slide, total_slides, art_style, theme_style, primary_color,
                audience, image_role, raw_prompt
            )
            prompts_export.append(rich_entry)

            # Check smart match first (from --images-dir analysis)
            if slide.slide_number in smart_match:
                assignment = smart_match[slide.slide_number]
                rprint(f"  [Matched] Slide {slide.slide_number}: "
                       f"{os.path.basename(assignment.image_path)} "
                       f"({assignment.confidence:.0%})")
                image_manifest[slide.slide_number] = {
                    'path': assignment.image_path,
                    'status': 'user',
                    'role': image_role,
                }
                cache.record(slide.slide_number, raw_prompt, current_theme, 'user', slide.title)
                stats['matched'] += 1
                continue

            # Check for numbered user images (user_slide_N.png / slide_N.png)
            user_img = self._find_user_image(slide.slide_number)
            if user_img:
                rprint(f"  [User] Using user-provided image for Slide {slide.slide_number}: {user_img}")
                image_manifest[slide.slide_number] = {
                    'path': user_img, 'status': 'user', 'role': image_role
                }
                cache.record(slide.slide_number, raw_prompt, current_theme, 'user', slide.title)
                stats['cache'] += 1
                continue

            # Check cache
            if cache.is_current(slide.slide_number, raw_prompt, current_theme, out_path, force):
                rprint(f"  [Cache] Slide {slide.slide_number} unchanged — skipping.")
                image_manifest[slide.slide_number] = {
                    'path': out_path, 'status': 'cache', 'role': image_role
                }
                stats['cache'] += 1
                continue

            # P3 infographic: skip API, go straight to gradient (save quota)
            if priority >= 3 and not force:
                rprint(f"  [Skip] Slide {slide.slide_number} ({slide.layout_type}) is P3 — using gradient.")
                self._generate_gradient(current_theme, primary_color, out_path, slide.slide_number)
                image_manifest[slide.slide_number] = {
                    'path': out_path, 'status': 'fallback', 'role': image_role
                }
                cache.record(slide.slide_number, raw_prompt, current_theme, 'fallback', slide.title)
                stats['fallback'] += 1
                continue

            # Try API generation
            if self.has_api:
                if not self._rate_limiter.wait_if_needed():
                    # Rate limit timeout — fall back to gradient
                    self._generate_gradient(current_theme, primary_color, out_path, slide.slide_number)
                    image_manifest[slide.slide_number] = {
                        'path': out_path, 'status': 'fallback', 'role': image_role
                    }
                    cache.record(slide.slide_number, raw_prompt, current_theme, 'fallback', slide.title)
                    stats['fallback'] += 1
                    continue

                success, retry_delay = self._generate_with_api(raw_prompt, out_path)
                if success:
                    self._rate_limiter.record_success()
                    image_manifest[slide.slide_number] = {
                        'path': out_path, 'status': 'api', 'role': image_role
                    }
                    cache.record(slide.slide_number, raw_prompt, current_theme, 'api', slide.title)
                    stats['api'] += 1
                else:
                    if retry_delay:
                        self._rate_limiter.record_429(retry_delay)
                    self._generate_gradient(current_theme, primary_color, out_path, slide.slide_number)
                    image_manifest[slide.slide_number] = {
                        'path': out_path, 'status': 'fallback', 'role': image_role
                    }
                    cache.record(slide.slide_number, raw_prompt, current_theme, 'fallback', slide.title)
                    stats['fallback'] += 1
            else:
                # Offline mode — generate gradient
                self._generate_gradient(current_theme, primary_color, out_path, slide.slide_number)
                image_manifest[slide.slide_number] = {
                    'path': out_path, 'status': 'fallback', 'role': image_role
                }
                cache.record(slide.slide_number, raw_prompt, current_theme, 'fallback', slide.title)
                stats['fallback'] += 1

        # Save cache
        cache.save()

        # Export prompts file
        if prompts_export:
            self._export_prompts(prompts_export)

        # Placeholder PNG for templates
        placeholder_path = os.path.join(self.assets_dir, "placeholder.png")
        self._generate_gradient(current_theme, primary_color, placeholder_path, seed=99)

        # Print summary
        total = sum(stats.values())
        if total:
            parts = []
            if stats['matched']:
                parts.append(f"{stats['matched']} matched")
            if stats['api']:
                parts.append(f"{stats['api']} API")
            if stats['cache']:
                parts.append(f"{stats['cache']} cached")
            if stats['fallback']:
                parts.append(f"{stats['fallback']} gradients")
            rprint(f"  ImageGenerator: {', '.join(parts)} — {total} images processed.")

        return image_manifest

    # ─── helpers ────────────────────────────────────────────────────────

    def _find_user_image(self, slide_number: int) -> str:
        """Check for user-provided image: user_slide_N.{ext}"""
        for ext in ('png', 'jpg', 'jpeg', 'webp'):
            path = os.path.join(self.assets_dir, f"user_slide_{slide_number}.{ext}")
            if os.path.exists(path):
                return path
        return ''

    def _generate_gradient(
        self,
        structural_class: str,
        primary_color: str,
        out_path: str,
        seed: int = 0,
    ):
        rprint(f"  [Gradient] Generating theme gradient for: {os.path.basename(out_path)}")
        try:
            self._gradient_gen.generate(
                structural_class=structural_class,
                primary_hex=primary_color or None,
                out_path=out_path,
                seed=seed,
            )
        except Exception as e:
            rprint(f"  [Gradient] Failed: {e} — using grey fallback.")
            self._grey_fallback(out_path)

    def _grey_fallback(self, out_path: str):
        """Last-resort 1×1 grey image (never should reach this)."""
        img = Image.new('RGB', (1920, 1080), color=(40, 40, 50))
        img.save(out_path)

    def _generate_with_api(self, prompt: str, out_path: str) -> tuple:
        """
        Returns (success: bool, retry_delay_seconds: int | None)
        """
        rprint(f"  [API] Generating image: '{prompt[:60]}...'")
        try:
            response = self.client.models.generate_content(
                model='gemini-3.1-flash-image',
                contents=prompt,
            )
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        with open(out_path, "wb") as f:
                            f.write(part.inline_data.data)
                        rprint(f"  [API] Saved to {out_path}")
                        return True, None
            rprint("  [API] No image returned in response.")
            return False, None
        except Exception as e:
            err_str = str(e)
            delay_match = re.search(r"retryDelay.*?(\d+)s", err_str)
            retry_delay = int(delay_match.group(1)) if delay_match else 30
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Try rotating to next API key
                if len(self._keys) > 1:
                    old_idx = self._key_idx
                    self._key_idx = (self._key_idx + 1) % len(self._keys)
                    try:
                        from ppt_maker.core.api_keys import get_client
                    except ImportError:
                        from api_keys import get_client
                    self.client, self._key_idx = get_client(self._key_idx)
                    rprint(f"  [RateLimit] Key #{old_idx+1} → key #{self._key_idx+1}")
                    return False, 2  # Short retry delay since we switched keys
                rprint(f"  [RateLimit] 429 — retry in {retry_delay}s. Using gradient fallback.")
                return False, retry_delay
            else:
                rprint(f"  [API Error] {err_str[:200]}")
                return False, None

    def _role_instructions(self, role: str) -> str:
        instructions = {
            'background': (
                "Full-bleed background. Keep center clear — text overlays on top. "
                "Use depth and subtle focus blur in the center zone."
            ),
            'supporting': (
                "Supporting visual beside text (right half of slide). "
                "Should visually reinforce the slide's key message."
            ),
            'data': (
                "Data visualization / diagram — this IS the main content. "
                "Clear, professional, readable. No decorative clutter."
            ),
            'decorative': (
                "Decorative texture at 15–30% opacity. "
                "Adds visual depth without competing with text."
            ),
        }
        return instructions.get(role, instructions['background'])

    def _build_prompt_entry(
        self, slide, total_slides, art_style, theme_style,
        primary_color, audience, image_role, raw_prompt
    ) -> str:
        lines = [
            f"--- Slide {slide.slide_number} of {total_slides} ---",
            f"Save as: assets/slide_{slide.slide_number}.png",
            "",
            f"Slide Title: {slide.title}",
            f"Layout Type: {slide.layout_type}",
            f"Image Role: {image_role}",
            f"Audience: {audience}" if audience else None,
            "",
            "IMAGE REQUIREMENTS:",
            f"  - Dimensions: 1920 x 1080px (16:9 landscape)",
            (f"  - Theme: {theme_style}" + (f", primary accent: {primary_color}" if primary_color else "")) if theme_style else None,
            f"  - Art style: {art_style}" if art_style else None,
            f"  - Usage: {self._role_instructions(image_role)}",
            "  - No text, logos, or watermarks.",
            "",
            "PROMPT:",
            f"  {raw_prompt}",
        ]
        return "\n".join(line for line in lines if line is not None)

    def _export_prompts(self, prompts_export: list):
        prompts_path = os.path.join(self.assets_dir, "image_prompts.txt")
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write("=== MANUAL IMAGE GENERATION PROMPTS ===\n")
            f.write("Copy each block into Gemini, ChatGPT, or Midjourney.\n")
            f.write("Save each image to the path shown in 'Save as:'.\n")
            f.write("Then re-run: python cli.py generate --offline-plan master_plan.json\n")
            f.write("=" * 55 + "\n\n")
            f.write("\n\n".join(prompts_export))
            f.write("\n")
        rprint(f"  [Export] Saved image prompts to {prompts_path}")
