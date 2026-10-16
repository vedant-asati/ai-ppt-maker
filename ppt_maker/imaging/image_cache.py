"""
image_cache.py — Content-aware image cache.

Stores a .image_cache.json manifest in the assets directory.
Invalidates on: prompt change, theme change, or force flag.
"""

import os
import json
import hashlib
import time
from typing import Optional


class ImageCache:
    CACHE_FILE = '.image_cache.json'

    def __init__(self, assets_dir: str = 'assets'):
        self.assets_dir = assets_dir
        self.cache_path = os.path.join(assets_dir, self.CACHE_FILE)
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save(self):
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            print(f"  [Cache] Warning: could not save cache: {e}")

    def _hash_prompt(self, prompt: str) -> str:
        prompt = (prompt or '').strip()
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()[:8]

    def is_current(
        self,
        slide_number: int,
        prompt: str,
        theme: str,
        image_path: str,
        force: bool = False,
    ) -> bool:
        """
        Returns True if the cached image is still valid (no need to regenerate).
        False if: force=True, file missing, theme changed, or prompt hash changed.
        """
        if force:
            return False

        if not os.path.exists(image_path):
            return False

        key = str(slide_number)
        entry = self._data.get('slides', {}).get(key)
        if not entry:
            return False

        # Theme changed?
        if self._data.get('theme') != theme:
            return False

        # Prompt hash changed?
        if entry.get('prompt_hash') != self._hash_prompt(prompt):
            return False

        return True

    def record(
        self,
        slide_number: int,
        prompt: str,
        theme: str,
        status: str,
        title: str = '',
    ):
        """Record a generated (or skipped) image in the cache."""
        if 'slides' not in self._data:
            self._data['slides'] = {}

        self._data['theme'] = theme
        self._data['generated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        self._data['slides'][str(slide_number)] = {
            'prompt_hash': self._hash_prompt(prompt),
            'status': status,         # api | cache | fallback | user
            'slide_title': title,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }

    def get_status(self, slide_number: int) -> Optional[str]:
        return self._data.get('slides', {}).get(str(slide_number), {}).get('status')

    def theme_changed(self, new_theme: str) -> bool:
        cached_theme = self._data.get('theme')
        return bool(cached_theme and cached_theme != new_theme)

    def clear(self):
        self._data = {}
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
