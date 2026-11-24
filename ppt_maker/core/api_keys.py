"""
API key rotation utility for Gemini.

Loads all GEMINI_API_KEY* environment variables and provides
automatic key rotation when one key hits a 429 rate limit.

Usage:
    from api_keys import get_api_keys, rotate_client

    keys = get_api_keys()              # ['key1', 'key2', ...]
    client = rotate_client()           # genai.Client with first available key
    client = rotate_client(exclude=0)  # skip key at index 0
"""

import os
import threading
from typing import List, Optional, Tuple
import httpx
from google import genai
from google.genai import types


def _create_genai_client(api_key: str, timeout_seconds: float = 45.0) -> genai.Client:
    """Instantiate genai.Client with a strict HTTP socket timeout to prevent indefinite hangs."""
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            httpx_client=httpx.Client(timeout=timeout_seconds)
        )
    )


def get_api_keys() -> List[str]:
    """
    Load all Gemini API keys from environment.
    Looks for GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.
    """
    keys = []

    # Primary key
    primary = os.environ.get("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)

    # Numbered keys: GEMINI_API_KEY_1, _2, _3, ...
    for i in range(1, 10):
        key = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        if key and key not in keys:
            keys.append(key)

    return keys


class APIKeyRotator:
    """
    Thread-safe round-robin API key rotator for multi-agent parallel execution.
    Automatically distributes requests across available keys and handles rate-limit rotation.
    """
    def __init__(self, keys: Optional[List[str]] = None):
        self._keys = keys if keys is not None else get_api_keys()
        self._index = 0
        self._lock = threading.Lock()

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def get_client(self):
        """Returns (client, key_index) in round-robin sequence."""
        if not self._keys:
            return None, -1
        with self._lock:
            idx = self._index % len(self._keys)
            self._index += 1
        return _create_genai_client(self._keys[idx]), idx

    def rotate_on_error(self, failed_index: int):
        """Advances past failed_index upon encountering HTTP 429 and returns a fresh client."""
        if not self._keys:
            return None, -1
        with self._lock:
            if len(self._keys) > 1:
                next_idx = (failed_index + 1) % len(self._keys)
                self._index = next_idx + 1
            else:
                next_idx = 0
        return _create_genai_client(self._keys[next_idx]), next_idx


# Global default rotator
_DEFAULT_ROTATOR: Optional[APIKeyRotator] = None
_ROTATOR_LOCK = threading.Lock()


def get_rotator() -> APIKeyRotator:
    global _DEFAULT_ROTATOR
    if _DEFAULT_ROTATOR is None:
        with _ROTATOR_LOCK:
            if _DEFAULT_ROTATOR is None:
                _DEFAULT_ROTATOR = APIKeyRotator()
    return _DEFAULT_ROTATOR


def get_client(key_index: int = 0):
    """
    Create a genai.Client using the API key at the given index.
    Returns (client, key_index) or (None, -1) if no keys available.
    """
    keys = get_api_keys()
    if not keys:
        return None, -1

    idx = key_index % len(keys)
    return _create_genai_client(keys[idx]), idx


def rotate_client(exclude: int = -1):
    """
    Create a genai.Client using the next available key,
    skipping the key at `exclude` index (e.g., the one that just 429'd).

    Returns (client, key_index) or (None, -1) if no keys available.
    """
    keys = get_api_keys()
    if not keys:
        return None, -1

    for i in range(len(keys)):
        if i == exclude:
            continue
        return _create_genai_client(keys[i]), i

    return _create_genai_client(keys[0]), 0

