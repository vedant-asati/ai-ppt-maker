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
from typing import List, Optional


def get_api_keys() -> List[str]:
    """
    Load all Gemini API keys from environment.
    Looks for GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.
    """
    keys = []

    # Primary key
    primary = os.environ.get("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)

    # Numbered keys: GEMINI_API_KEY_2, _3, _4, ...
    for i in range(2, 10):
        key = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        if key:
            keys.append(key)

    return keys


def get_client(key_index: int = 0):
    """
    Create a genai.Client using the API key at the given index.
    Returns (client, key_index) or (None, -1) if no keys available.
    """
    from google import genai

    keys = get_api_keys()
    if not keys:
        return None, -1

    idx = key_index % len(keys)
    return genai.Client(api_key=keys[idx]), idx


def rotate_client(exclude: int = -1):
    """
    Create a genai.Client using the next available key,
    skipping the key at `exclude` index (e.g., the one that just 429'd).

    Returns (client, key_index) or (None, -1) if no keys available.
    """
    from google import genai

    keys = get_api_keys()
    if not keys:
        return None, -1

    for i in range(len(keys)):
        if i == exclude:
            continue
        return genai.Client(api_key=keys[i]), i

    # All keys excluded — return the first one anyway
    return genai.Client(api_key=keys[0]), 0
