"""
image_validator.py — PIL-based image quality checks for generated slide images.

Runs after image generation, before templating. Flags images that are:
  - Wrong dimensions
  - Too dark or too bright (unusable as backgrounds)
  - Too low contrast (flat / washed out)
  - Center-heavy (text overlay area is cluttered)

Returns a list of ImageIssue objects the QualityChecker can report.
"""

import os
import math
from typing import List, Optional
from dataclasses import dataclass, field

try:
    from PIL import Image, ImageStat
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


@dataclass
class ImageIssue:
    slide_number: int
    image_path: str
    severity: str          # 'warning' | 'error'
    issue_type: str
    message: str
    metric: Optional[float] = None


class ImageValidator:
    # Thresholds
    MIN_WIDTH   = 960
    MIN_HEIGHT  = 540
    TARGET_W    = 1920
    TARGET_H    = 1080

    BRIGHTNESS_MIN = 15    # Too dark (0–255)
    BRIGHTNESS_MAX = 225   # Too bright
    CONTRAST_MIN   = 20    # Std dev of luminance — flat if below
    CENTER_CLUTTER_MAX = 0.35  # Edge-to-center brightness ratio

    def validate(self, image_path: str, slide_number: int) -> List[ImageIssue]:
        """Validate a single image file. Returns list of issues (empty = OK)."""
        issues: List[ImageIssue] = []

        if not _PIL_AVAILABLE:
            return issues  # Skip silently

        if not os.path.exists(image_path):
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='error',
                issue_type='FILE_MISSING',
                message=f"Image file not found: {image_path}",
            ))
            return issues

        try:
            img = Image.open(image_path)
        except Exception as e:
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='error',
                issue_type='UNREADABLE',
                message=f"Cannot open image: {e}",
            ))
            return issues

        w, h = img.size

        # ── 1. Dimension check ────────────────────────────────────────────
        if w < self.MIN_WIDTH or h < self.MIN_HEIGHT:
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='error',
                issue_type='DIMENSIONS_TOO_SMALL',
                message=f"Image is {w}×{h}px — minimum is {self.MIN_WIDTH}×{self.MIN_HEIGHT}.",
                metric=float(w),
            ))

        if w < self.TARGET_W or h < self.TARGET_H:
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='warning',
                issue_type='DIMENSIONS_SUBOPTIMAL',
                message=f"Image is {w}×{h}px — recommended is {self.TARGET_W}×{self.TARGET_H}. "
                        f"May appear slightly soft in PDF.",
                metric=float(w),
            ))

        # ── 2. Convert to RGB for analysis ───────────────────────────────
        try:
            rgb = img.convert('RGB')
        except Exception:
            return issues  # Can't analyze

        # ── 3. Global brightness check ────────────────────────────────────
        stat = ImageStat.Stat(rgb)
        mean_brightness = sum(stat.mean) / 3  # Average across R, G, B
        if mean_brightness < self.BRIGHTNESS_MIN:
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='warning',
                issue_type='TOO_DARK',
                message=f"Image is very dark (brightness={mean_brightness:.1f}/255). "
                        f"Text overlay may be invisible.",
                metric=mean_brightness,
            ))
        elif mean_brightness > self.BRIGHTNESS_MAX:
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='warning',
                issue_type='TOO_BRIGHT',
                message=f"Image is very bright (brightness={mean_brightness:.1f}/255). "
                        f"Dark text may be unreadable.",
                metric=mean_brightness,
            ))

        # ── 4. Contrast check ─────────────────────────────────────────────
        mean_contrast = sum(stat.stddev) / 3
        if mean_contrast < self.CONTRAST_MIN:
            issues.append(ImageIssue(
                slide_number=slide_number,
                image_path=image_path,
                severity='warning',
                issue_type='LOW_CONTRAST',
                message=f"Image is low contrast (stddev={mean_contrast:.1f}). "
                        f"Looks flat — consider a more dynamic image.",
                metric=mean_contrast,
            ))

        # ── 5. Center complexity check (for background images) ────────────
        # Background images should have a calmer center (where text overlays)
        # and more visual interest at the edges.
        try:
            center_brightness = self._center_brightness(rgb)
            edge_brightness   = self._edge_brightness(rgb)
            if edge_brightness > 0:
                ratio = center_brightness / edge_brightness
                if ratio > (1 + self.CENTER_CLUTTER_MAX):
                    issues.append(ImageIssue(
                        slide_number=slide_number,
                        image_path=image_path,
                        severity='warning',
                        issue_type='CENTER_CLUTTERED',
                        message=f"Image center ({center_brightness:.0f}) is brighter than edges "
                                f"({edge_brightness:.0f}). Text overlays may be unreadable.",
                        metric=ratio,
                    ))
        except Exception:
            pass  # Non-critical

        return issues

    def validate_all(self, image_manifest: dict) -> List[ImageIssue]:
        """Validate all images in an image_manifest dict."""
        all_issues = []
        for slide_num, info in image_manifest.items():
            path = info.get('path', '')
            if path:
                all_issues.extend(self.validate(path, int(slide_num)))
        return all_issues

    def _center_brightness(self, img: 'Image.Image') -> float:
        """Average brightness of the center 40% of the image."""
        w, h = img.size
        cx, cy = w // 2, h // 2
        cw, ch = int(w * 0.4), int(h * 0.4)
        crop = img.crop((cx - cw//2, cy - ch//2, cx + cw//2, cy + ch//2))
        stat = ImageStat.Stat(crop)
        return sum(stat.mean) / 3

    def _edge_brightness(self, img: 'Image.Image') -> float:
        """Average brightness of the outer 20% border of the image."""
        w, h = img.size
        bw, bh = int(w * 0.2), int(h * 0.2)
        strips = [
            img.crop((0, 0, w, bh)),           # top
            img.crop((0, h - bh, w, h)),        # bottom
            img.crop((0, bh, bw, h - bh)),      # left
            img.crop((w - bw, bh, w, h - bh)),  # right
        ]
        values = []
        for strip in strips:
            stat = ImageStat.Stat(strip)
            values.append(sum(stat.mean) / 3)
        return sum(values) / len(values) if values else 0
