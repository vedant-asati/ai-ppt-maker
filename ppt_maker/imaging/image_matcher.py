"""
Smart image-to-slide matching using Gemini vision.

Analyzes user-supplied images and assigns them to presentation slides
based on visual content, layout suitability, and topic relevance.

Usage:
    matcher = ImageMatcher(api_key="...")
    result = matcher.match("./my_photos", slides)
    # result.assignments[slide_number] → ImageAssignment
"""

import os
import re
import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from PIL import Image
from rich import print as rprint


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ImageAssignment:
    slide_number: int
    image_path: str
    confidence: float
    reason: str
    description: str


@dataclass
class ImageMatchResult:
    assignments: Dict[int, ImageAssignment]    # slide_number → assignment
    unmatched_images: List[str]                # paths of unused images
    unmatched_slides: List[int]                # slide numbers without images
    descriptions: Dict[str, str]               # path → description


# ─────────────────────────────────────────────────────────────────────────────
# Layout-specific suitability rules (embedded in Gemini prompt)
# ─────────────────────────────────────────────────────────────────────────────

_LAYOUT_RULES = """\
Layout suitability guide:
- cover: dramatic landscapes, wide shots, bold subjects — full-bleed background behind title
- split: clear subject/person, medium shot — sits beside text in the right half
- quote: atmospheric, moody, nature, abstract — goes behind quote text (must not compete)
- stat/infographic: charts, graphs, data visualizations, diagrams — supporting data visual
- generic: almost anything works — used as low-opacity decorative background
- timeline: rarely needs an image — only assign if it perfectly matches the process/steps\
"""

# Noise words to strip from filenames in offline mode
_FILENAME_NOISE = {
    'img', 'image', 'images', 'dsc', 'dscn', 'photo', 'pic', 'screenshot',
    'screen', 'shot', 'capture', 'copy', 'final', 'edit', 'edited', 'new',
    'untitled', 'download', 'downloaded', 'temp', 'tmp', 'test',
}


# ─────────────────────────────────────────────────────────────────────────────
# ImageMatcher
# ─────────────────────────────────────────────────────────────────────────────

class ImageMatcher:
    """Analyze user images and assign them to slides using Gemini vision."""

    def __init__(self, api_key: str = None, cache_dir: str = 'assets'):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.has_api = bool(self.api_key)
        self.cache_dir = cache_dir
        self._cache_path = os.path.join(cache_dir, '.image_match_cache.json')

    # ─── Public API ──────────────────────────────────────────────────────

    def match(
        self,
        images_dir: str,
        slides: list,
        min_confidence: float = 0.4,
        upgrade_threshold: float = 0.8,
    ) -> ImageMatchResult:
        """
        Analyze images in `images_dir` and assign them to slides.

        Args:
            images_dir: Directory containing user images.
            slides: List of Slide objects from MasterPlan.
            min_confidence: Minimum confidence to accept a match (0-1).
            upgrade_threshold: If confidence exceeds this, can upgrade
                              requires_image=False slides to use the image.

        Returns:
            ImageMatchResult with assignments and diagnostics.
        """
        rprint("ImageMatcher: Analyzing user images...")

        # Step 1: Scan and validate images
        valid_images = self._scan_images(images_dir)
        if not valid_images:
            rprint("  [Warning] No valid images found in directory.")
            return ImageMatchResult(
                assignments={},
                unmatched_images=[],
                unmatched_slides=[s.slide_number for s in slides],
                descriptions={},
            )

        rprint(f"  Found {len(valid_images)} valid images.")

        # Step 2: Check cache
        cache_key = self._compute_cache_key(images_dir, valid_images, slides)
        cached = self._load_cache(cache_key)
        if cached:
            rprint(f"  [Cache] Using cached match results.")
            return cached

        # Step 3: Match (Gemini or offline)
        if self.has_api:
            result = self._match_with_gemini(
                valid_images, slides, min_confidence, upgrade_threshold
            )
        else:
            rprint("  [Offline] No API key — using filename + PIL heuristics.")
            result = self._match_offline(
                valid_images, slides, min_confidence
            )

        # Step 4: Cache result
        self._save_cache(cache_key, result)

        # Step 5: Print summary
        self._print_summary(result)

        return result

    # ─── Image Scanning & Validation ─────────────────────────────────────

    def _scan_images(self, images_dir: str) -> List[dict]:
        """
        Scan directory for valid images. Returns list of dicts:
        [{ 'path': str, 'filename': str, 'width': int, 'height': int,
           'aspect': float, 'size_kb': int }]
        """
        _EXTS = {'.png', '.jpg', '.jpeg', '.webp'}
        valid = []

        for fname in sorted(os.listdir(images_dir)):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _EXTS:
                continue

            path = os.path.join(images_dir, fname)
            size_kb = os.path.getsize(path) // 1024

            # Skip tiny/corrupt files
            if size_kb < 10:
                rprint(f"  [Skip] {fname}: too small ({size_kb}KB)")
                continue

            try:
                with Image.open(path) as img:
                    w, h = img.size
            except Exception as e:
                rprint(f"  [Skip] {fname}: corrupt ({e})")
                continue

            # Skip very low resolution
            if w < 400 or h < 300:
                rprint(f"  [Skip] {fname}: too small ({w}×{h})")
                continue

            valid.append({
                'path': os.path.abspath(path),
                'filename': fname,
                'width': w,
                'height': h,
                'aspect': round(w / h, 2),
                'size_kb': size_kb,
            })

        return valid

    # ─── Gemini Vision Matching ──────────────────────────────────────────

    # Maximum images to send per Gemini request.
    # Gemini supports ~20 inline images reliably; we use 16 as a safe ceiling.
    _GEMINI_IMAGE_BATCH_SIZE = 16

    def _match_with_gemini(
        self,
        images: List[dict],
        slides: list,
        min_confidence: float,
        upgrade_threshold: float,
    ) -> ImageMatchResult:
        """
        Multi-modal Gemini call: images + slides → mapping.

        For large image sets (>16), splits into batches and merges results
        keeping the highest-confidence assignment per slide.
        """
        try:
            from ppt_maker.core.api_keys import get_api_keys
        except ImportError:
            from api_keys import get_api_keys

        keys = get_api_keys()
        if not keys:
            rprint("  [Warning] No API keys found — using offline matching.")
            return self._match_offline(images, slides, min_confidence)

        if len(images) <= self._GEMINI_IMAGE_BATCH_SIZE:
            # Fast path — single call
            return self._match_batch_with_gemini(
                images, slides, min_confidence, upgrade_threshold, batch_index=0
            )

        # Batch path — split into chunks
        chunks = [
            images[i:i + self._GEMINI_IMAGE_BATCH_SIZE]
            for i in range(0, len(images), self._GEMINI_IMAGE_BATCH_SIZE)
        ]
        rprint(
            f"  [Batch] {len(images)} images → {len(chunks)} batches "
            f"of ≤{self._GEMINI_IMAGE_BATCH_SIZE} each."
        )

        # Run each batch, then merge
        merged = ImageMatchResult(
            assignments={}, unmatched_images=[], unmatched_slides=[], descriptions={}
        )
        for i, chunk in enumerate(chunks):
            rprint(f"  [Batch {i+1}/{len(chunks)}] {len(chunk)} images...")
            batch_result = self._match_batch_with_gemini(
                chunk, slides, min_confidence, upgrade_threshold, batch_index=i
            )
            merged = self._merge_results(merged, batch_result)

        # Compute final unmatched lists from merged
        all_image_paths = {img['path'] for img in images}
        assigned_paths = {a.image_path for a in merged.assignments.values()}
        slides_needing = {s.slide_number for s in slides if s.requires_image}
        merged.unmatched_images = sorted(all_image_paths - assigned_paths)
        merged.unmatched_slides = sorted(slides_needing - set(merged.assignments.keys()))
        return merged

    def _merge_results(
        self, base: 'ImageMatchResult', incoming: 'ImageMatchResult'
    ) -> 'ImageMatchResult':
        """
        Merge two ImageMatchResult objects.
        For conflicting slide assignments, keep the higher-confidence one.
        Descriptions are union-merged (new descriptions don't overwrite existing).
        """
        # Merge descriptions
        merged_descriptions = {**incoming.descriptions, **base.descriptions}

        # Merge assignments — higher confidence wins
        merged_assignments = dict(base.assignments)
        for slide_num, incoming_assign in incoming.assignments.items():
            existing = merged_assignments.get(slide_num)
            if existing is None or incoming_assign.confidence > existing.confidence:
                merged_assignments[slide_num] = incoming_assign

        return ImageMatchResult(
            assignments=merged_assignments,
            unmatched_images=[],   # recomputed after all batches
            unmatched_slides=[],   # recomputed after all batches
            descriptions=merged_descriptions,
        )

    def _match_batch_with_gemini(
        self,
        images: List[dict],
        slides: list,
        min_confidence: float,
        upgrade_threshold: float,
        batch_index: int = 0,
    ) -> ImageMatchResult:
        """Single Gemini call for one batch of images against all slides."""
        from google.genai import types
        try:
            from ppt_maker.core.api_keys import get_api_keys, get_client
        except ImportError:
            from api_keys import get_api_keys, get_client

        keys = get_api_keys()

        # Build the slide table
        slide_table = self._build_slide_table(slides)

        # Build the prompt (offset IMAGE labels if this is a later batch)
        label_offset = batch_index * self._GEMINI_IMAGE_BATCH_SIZE
        prompt = self._build_gemini_prompt(images, slide_table, label_offset=label_offset)

        # Build content parts: prompt text + batch images
        contents = [prompt]
        for img_info in images:
            try:
                with Image.open(img_info['path']) as raw_img:
                    pil_img = raw_img.copy()
                # Resize large images to save tokens (max 1280px on longest side)
                max_dim = max(pil_img.size)
                if max_dim > 1280:
                    scale = 1280 / max_dim
                    new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
                    pil_img = pil_img.resize(new_size, Image.LANCZOS)
                contents.append(pil_img)
            except Exception as e:
                rprint(f"  [Warning] Could not load {img_info['filename']}: {e}")

        rprint(f"  [API] Sending {len(images)} images + {len(slides)} slides to Gemini...")

        # Try each API key on 429
        last_error = None
        for key_idx in range(len(keys)):
            client, _ = get_client(key_idx)
            if key_idx > 0:
                rprint(f"  [Retry] Trying API key #{key_idx + 1}...")
            try:
                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',  # 500 RPD free tier
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=4000,
                    ),
                )

                if response.usage_metadata:
                    rprint(
                        f"  [API] Tokens: {response.usage_metadata.total_token_count} "
                        f"(in={response.usage_metadata.prompt_token_count}, "
                        f"out={response.usage_metadata.candidates_token_count})"
                    )

                return self._parse_gemini_response(
                    response.text, images, slides, min_confidence, upgrade_threshold,
                    label_offset=label_offset,
                )

            except Exception as e:
                err_str = str(e)
                last_error = err_str
                if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                    rprint(f"  [429] Key #{key_idx + 1} rate-limited.")
                    continue  # Try next key
                else:
                    rprint(f"  [API Error] {err_str[:200]}")
                    break  # Non-rate-limit error — don't retry

        rprint("  [Fallback] All keys exhausted — switching to offline matching for this batch.")
        return self._match_offline(images, slides, min_confidence)

    def _build_slide_table(self, slides: list) -> str:
        """Format slides as a readable table for the prompt."""
        lines = []
        for s in slides:
            img_prompt = (getattr(s, 'image_prompt', '') or '')[:80]
            needs_img = 'YES' if s.requires_image else 'optional'
            role = getattr(s, 'image_role', 'background') or 'background'
            lines.append(
                f"  Slide {s.slide_number}: layout={s.layout_type}, "
                f"title=\"{s.title}\", "
                f"needs_image={needs_img}, image_role={role}, "
                f"prompt=\"{img_prompt}\""
            )
        return "\n".join(lines)

    def _build_gemini_prompt(self, images: List[dict], slide_table: str, label_offset: int = 0) -> str:
        """Build the Gemini prompt. label_offset shifts IMAGE_N labels for batch runs."""
        image_list = "\n".join(
            f"  IMAGE_{label_offset + i + 1}: {img['filename']} ({img['width']}×{img['height']})"
            for i, img in enumerate(images)
        )

        return f"""\
You are an image-to-slide matcher for a presentation tool.

## Images (provided in order after this text)
{image_list}

## Slides
{slide_table}

## {_LAYOUT_RULES}

## Rules
1. Each image may be assigned to AT MOST one slide.
2. Only assign if the image genuinely fits the slide's topic AND layout type.
3. Consider the slide's image_prompt — it describes what the ideal image would look like.
4. Consider image quality: sharp, well-lit photos are preferred over blurry ones.
5. Landscape images (wide) are better for cover/background roles.
6. Portrait images (tall) are better for split/supporting roles.
7. Charts/graphs/data visuals should go to stat or infographic slides.
8. For slides with needs_image=optional, only assign if confidence > 0.8.
9. Never force a match. It's better to leave a slide without an image than to assign a bad one.
10. Confidence is 0.0 (no match) to 1.0 (perfect match).

## Output (JSON only, no markdown fences)
{{
  "image_descriptions": {{
    "IMAGE_1": "10-15 word description of what this image shows",
    ...
  }},
  "assignments": [
    {{
      "image_label": "IMAGE_1",
      "slide_number": 2,
      "confidence": 0.85,
      "reason": "Brief explanation of why this image fits this slide"
    }}
  ]
}}
"""

    def _parse_gemini_response(
        self,
        response_text: str,
        images: List[dict],
        slides: list,
        min_confidence: float,
        upgrade_threshold: float,
        label_offset: int = 0,
    ) -> ImageMatchResult:
        """Parse Gemini JSON response into ImageMatchResult."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fences
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                rprint("  [Parse Error] Could not parse Gemini response.")
                return ImageMatchResult(
                    assignments={},
                    unmatched_images=[img['path'] for img in images],
                    unmatched_slides=[s.slide_number for s in slides if s.requires_image],
                    descriptions={},
                )

        # Build label→path mapping using label_offset for batch consistency
        # e.g. batch_index=1, offset=16 → IMAGE_17, IMAGE_18 ...
        label_to_img = {
            f"IMAGE_{label_offset + i + 1}": img for i, img in enumerate(images)
        }

        # Parse descriptions
        descriptions = {}
        for label, desc in data.get('image_descriptions', {}).items():
            if label in label_to_img:
                descriptions[label_to_img[label]['path']] = desc

        # Parse assignments
        assignments = {}
        assigned_images = set()
        slide_map = {s.slide_number: s for s in slides}

        for entry in data.get('assignments', []):
            label = entry.get('image_label', '')
            slide_num = entry.get('slide_number')
            confidence = float(entry.get('confidence', 0))
            reason = entry.get('reason', '')

            if label not in label_to_img:
                continue
            if slide_num not in slide_map:
                continue
            if confidence < min_confidence:
                continue

            slide = slide_map[slide_num]

            # For slides that don't require images, need higher threshold
            if not slide.requires_image and confidence < upgrade_threshold:
                continue

            img_info = label_to_img[label]
            if img_info['path'] in assigned_images:
                continue  # Already assigned

            desc = descriptions.get(img_info['path'], '')

            assignments[slide_num] = ImageAssignment(
                slide_number=slide_num,
                image_path=img_info['path'],
                confidence=confidence,
                reason=reason,
                description=desc,
            )
            assigned_images.add(img_info['path'])

        # Compute unmatched
        all_image_paths = {img['path'] for img in images}
        unmatched_images = sorted(all_image_paths - assigned_images)

        slides_needing_images = {
            s.slide_number for s in slides if s.requires_image
        }
        unmatched_slides = sorted(slides_needing_images - set(assignments.keys()))

        return ImageMatchResult(
            assignments=assignments,
            unmatched_images=unmatched_images,
            unmatched_slides=unmatched_slides,
            descriptions=descriptions,
        )

    # ─── Offline Fallback ────────────────────────────────────────────────

    def _match_offline(
        self,
        images: List[dict],
        slides: list,
        min_confidence: float,
    ) -> ImageMatchResult:
        """Offline matching using filename keywords + PIL heuristics."""
        # Extract keywords from each image filename
        img_keywords = {}
        for img in images:
            keywords = self._extract_filename_keywords(img['filename'])
            # Add PIL-based tags
            pil_tags = self._pil_classify(img)
            img_keywords[img['path']] = keywords | pil_tags

        # Score each image against each slide
        scores = {}  # (image_path, slide_number) → score
        for img in images:
            for slide in slides:
                if not slide.requires_image:
                    continue
                score = self._keyword_score(
                    img_keywords[img['path']],
                    slide,
                    img,
                )
                scores[(img['path'], slide.slide_number)] = score

        # Greedy assignment: pick highest score, assign, remove both
        assignments = {}
        assigned_images = set()
        assigned_slides = set()

        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        for (img_path, slide_num), score in sorted_scores:
            if img_path in assigned_images or slide_num in assigned_slides:
                continue
            if score < min_confidence:
                continue

            img_info = next(i for i in images if i['path'] == img_path)
            assignments[slide_num] = ImageAssignment(
                slide_number=slide_num,
                image_path=img_path,
                confidence=score,
                reason=f"Keyword match: {', '.join(img_keywords[img_path])}",
                description=f"{img_info['filename']} ({img_info['width']}×{img_info['height']})",
            )
            assigned_images.add(img_path)
            assigned_slides.add(slide_num)

        # Compute unmatched
        all_image_paths = {img['path'] for img in images}
        unmatched_images = sorted(all_image_paths - assigned_images)
        slides_needing_images = {
            s.slide_number for s in slides if s.requires_image
        }
        unmatched_slides = sorted(slides_needing_images - assigned_slides)

        return ImageMatchResult(
            assignments=assignments,
            unmatched_images=unmatched_images,
            unmatched_slides=unmatched_slides,
            descriptions={
                img['path']: f"Keywords: {', '.join(img_keywords[img['path']])}"
                for img in images
            },
        )

    def _extract_filename_keywords(self, filename: str) -> set:
        """Extract meaningful keywords from a filename."""
        name = os.path.splitext(filename)[0]

        # Split on common separators
        tokens = re.split(r'[_\-\s.]+', name)

        # Also split camelCase
        expanded = []
        for token in tokens:
            parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)', token)
            expanded.extend(parts if parts else [token])

        # Lowercase, filter noise
        keywords = set()
        for token in expanded:
            t = token.lower().strip()
            if len(t) < 2:
                continue
            if t in _FILENAME_NOISE:
                continue
            if t.isdigit():
                continue
            keywords.add(t)

        return keywords

    def _pil_classify(self, img_info: dict) -> set:
        """Basic PIL-based image classification (no ML)."""
        tags = set()

        # Aspect ratio classification
        aspect = img_info['aspect']
        if aspect > 1.5:
            tags.add('_landscape')
            tags.add('_wide')
        elif aspect < 0.75:
            tags.add('_portrait')
            tags.add('_tall')
        else:
            tags.add('_square')

        # Resolution tier
        w, h = img_info['width'], img_info['height']
        if w >= 1920 or h >= 1080:
            tags.add('_highres')

        try:
            with Image.open(img_info['path']) as pil_img:
                # Convert to RGB for analysis
                rgb = pil_img.convert('RGB').resize((200, 200))
                pixels = list(rgb.getdata())

                # Average brightness
                avg_brightness = sum(
                    0.299 * r + 0.587 * g + 0.114 * b
                    for r, g, b in pixels
                ) / len(pixels)

                if avg_brightness < 60:
                    tags.add('_dark')
                    tags.add('_moody')
                elif avg_brightness > 200:
                    tags.add('_bright')

                # Color variance (high = photo, low = chart/solid)
                r_vals = [p[0] for p in pixels]
                g_vals = [p[1] for p in pixels]
                b_vals = [p[2] for p in pixels]

                def variance(vals):
                    mean = sum(vals) / len(vals)
                    return sum((v - mean) ** 2 for v in vals) / len(vals)

                color_var = (variance(r_vals) + variance(g_vals) + variance(b_vals)) / 3
                if color_var < 500:
                    tags.add('_lowvariance')
                    tags.add('_chart')
                elif color_var > 3000:
                    tags.add('_colorful')
                    tags.add('_photo')

        except Exception:
            pass

        return tags

    def _keyword_score(self, img_keywords: set, slide, img_info: dict) -> float:
        """Score an image against a slide using keyword overlap."""
        # Build slide keywords from title, image_prompt, eyebrow
        slide_text = ' '.join(filter(None, [
            slide.title,
            getattr(slide, 'image_prompt', ''),
            getattr(slide, 'eyebrow', ''),
            getattr(slide, 'subtitle', ''),
        ])).lower()
        slide_words = set(re.findall(r'[a-z]+', slide_text))

        # Remove very common words
        _STOP = {'the', 'a', 'an', 'is', 'in', 'on', 'of', 'and', 'to', 'for',
                 'with', 'that', 'this', 'are', 'was', 'from', 'by', 'or', 'but'}
        slide_words -= _STOP
        content_keywords = img_keywords - {k for k in img_keywords if k.startswith('_')}

        if not slide_words or not content_keywords:
            # No keywords to match — use layout heuristics only
            return self._layout_heuristic_score(img_keywords, slide)

        # Jaccard-like overlap
        overlap = content_keywords & slide_words
        union = content_keywords | slide_words
        jaccard = len(overlap) / len(union) if union else 0

        # Layout bonus from PIL tags
        layout_bonus = self._layout_heuristic_score(img_keywords, slide)

        return min(1.0, jaccard * 0.7 + layout_bonus * 0.3)

    def _layout_heuristic_score(self, tags: set, slide) -> float:
        """Score based on PIL tags vs layout type."""
        layout = slide.layout_type
        score = 0.1  # base

        if layout == 'cover' and '_landscape' in tags:
            score += 0.3
        if layout == 'cover' and '_highres' in tags:
            score += 0.2
        if layout == 'split' and '_portrait' in tags:
            score += 0.3
        if layout == 'quote' and '_moody' in tags:
            score += 0.3
        if layout == 'quote' and '_dark' in tags:
            score += 0.2
        if layout in ('stat', 'infographic') and '_chart' in tags:
            score += 0.4
        if layout == 'generic' and '_photo' in tags:
            score += 0.2

        return min(1.0, score)

    # ─── Caching ─────────────────────────────────────────────────────────

    def _compute_cache_key(
        self, images_dir: str, images: List[dict], slides: list
    ) -> str:
        """Hash based on image filenames, sizes, and slide titles."""
        parts = [os.path.abspath(images_dir)]
        for img in sorted(images, key=lambda x: x['filename']):
            parts.append(f"{img['filename']}:{img['size_kb']}")
        for s in slides:
            parts.append(f"{s.slide_number}:{s.title}:{s.layout_type}")
        return hashlib.md5('|'.join(parts).encode()).hexdigest()

    def _load_cache(self, key: str) -> Optional[ImageMatchResult]:
        """Load cached result if available."""
        if not os.path.exists(self._cache_path):
            return None
        try:
            with open(self._cache_path, 'r') as f:
                cache = json.load(f)
            if cache.get('key') != key:
                return None
            data = cache['result']
            assignments = {
                int(sn): ImageAssignment(**a)
                for sn, a in data['assignments'].items()
            }
            return ImageMatchResult(
                assignments=assignments,
                unmatched_images=data['unmatched_images'],
                unmatched_slides=data['unmatched_slides'],
                descriptions=data['descriptions'],
            )
        except Exception:
            return None

    def _save_cache(self, key: str, result: ImageMatchResult):
        """Save result to cache."""
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            data = {
                'key': key,
                'timestamp': time.time(),
                'result': {
                    'assignments': {
                        str(sn): asdict(a)
                        for sn, a in result.assignments.items()
                    },
                    'unmatched_images': result.unmatched_images,
                    'unmatched_slides': result.unmatched_slides,
                    'descriptions': result.descriptions,
                },
            }
            with open(self._cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            rprint(f"  [Cache] Could not save: {e}")

    # ─── Output ──────────────────────────────────────────────────────────

    def _print_summary(self, result: ImageMatchResult):
        """Print a human-readable match summary."""
        if result.assignments:
            rprint(f"\n  ImageMatcher: Matched {len(result.assignments)} image(s) to slides:")
            for sn in sorted(result.assignments.keys()):
                a = result.assignments[sn]
                fname = os.path.basename(a.image_path)
                rprint(
                    f"    Slide {sn} ← {fname} "
                    f"(conf={a.confidence:.0%}: {a.reason})"
                )
        else:
            rprint("  ImageMatcher: No suitable matches found.")

        if result.unmatched_images:
            rprint(
                f"  Unused images: "
                f"{', '.join(os.path.basename(p) for p in result.unmatched_images)}"
            )
        if result.unmatched_slides:
            rprint(
                f"  Slides without images: "
                f"{', '.join(str(s) for s in result.unmatched_slides)} "
                f"→ will use gradient"
            )
        print()
