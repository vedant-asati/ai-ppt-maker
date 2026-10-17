"""
searcher.py — Lightweight web search discovery and query decomposition.

Provides:
  - QueryDecomposer: Decomposes a raw topic into 3 targeted, orthogonal search queries.
  - DuckDuckGoSearchProvider: Zero-key, lightweight search provider with backoff and timeout safety.
"""

import os
import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


class QueryDecomposer:
    """
    Decomposes a broad presentation topic into 3 focused search angles:
      1. Milestones & Current State
      2. Technical Challenges & Architectural Trade-offs
      3. Future Outlook, Timeline & Market Projections
    """

    def __init__(self, client=None):
        self.client = client

    def decompose(self, topic: str) -> List[str]:
        """
        Generates 3 focused sub-queries for the topic.
        Uses Gemini if client is available; falls back to deterministic heuristic queries.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            return ["general overview", "key challenges", "future outlook"]

        if self.client:
            try:
                from google.genai import types
                prompt = (
                    f"Given this presentation topic: '{clean_topic}'\n"
                    f"Generate exactly 3 focused search engine queries to gather comprehensive facts:\n"
                    f"1. Query 1: Major milestones, current progress, or recent breakthroughs\n"
                    f"2. Query 2: Technical architecture, core challenges, or trade-offs\n"
                    f"3. Query 3: Market adoption, future timeline, or projected impact\n"
                    f"Return ONLY a JSON array of 3 strings. Example: [\"query 1\", \"query 2\", \"query 3\"]"
                )
                response = self.client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=300,
                    )
                )
                import json
                queries = json.loads(response.text.strip())
                if isinstance(queries, list) and len(queries) >= 3:
                    return [str(q).strip() for q in queries[:3]]
            except Exception:
                pass

        # Deterministic heuristic decomposition (100% offline & robust)
        return [
            f"{clean_topic} overview recent milestones progress",
            f"{clean_topic} technical challenges architecture bottlenecks",
            f"{clean_topic} market projections timeline future outlook",
        ]


class DuckDuckGoSearchProvider:
    """
    Zero-key, lightweight search provider querying DuckDuckGo HTML / Lite interface.
    Includes rate-limit avoidance, timeout controls, and ad redirect decoding.
    """

    def __init__(self, timeout: float = 6.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @staticmethod
    def _decode_duckduckgo_url(raw_url: str) -> str:
        """Decodes DuckDuckGo redirect URLs like //duckduckgo.com/l/?uddg=https%3A%2F%2F..."""
        if "uddg=" in raw_url:
            parsed = urllib.parse.urlparse(raw_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in query_params and query_params["uddg"]:
                return query_params["uddg"][0]
        if raw_url.startswith("//"):
            return "https:" + raw_url
        return raw_url

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Executes search for a query and parses top search result titles, URLs, and snippets.
        """
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query, "b": ""}

        html = ""
        for attempt in range(self.max_retries):
            try:
                if _HAS_REQUESTS:
                    resp = requests.post(
                        url,
                        data=data,
                        headers=self.headers,
                        timeout=self.timeout
                    )
                    if resp.status_code == 200:
                        html = resp.text
                        break
                elif _HAS_HTTPX:
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(url, data=data, headers=self.headers)
                        if resp.status_code == 200:
                            html = resp.text
                            break
            except Exception:
                time.sleep(0.5 * (attempt + 1))

        if not html:
            return []

        return self._parse_html_results(html, max_results=max_results)

    def _parse_html_results(self, html: str, max_results: int = 3) -> List[Dict[str, str]]:
        """Parses results from DuckDuckGo HTML output."""
        results = []
        # Pattern for DuckDuckGo HTML results
        # Look for result__body / result__title and result__snippet
        result_blocks = re.findall(r'<div class="result__body">([\s\S]*?)</div>\s*</div>', html)
        if not result_blocks:
            result_blocks = re.findall(r'<div class="links_main links_deep result__body">([\s\S]*?)</div>', html)

        for block in result_blocks:
            # Title & link
            link_match = re.search(r'<a[^>]+class="result__url"[^>]+href="([^"]+)"', block)
            if not link_match:
                link_match = re.search(r'<a[^>]+class="result__snippet"[^>]+href="([^"]+)"', block)
            if not link_match:
                link_match = re.search(r'<a[^>]+href="([^"]+)"', block)

            title_match = re.search(r'<a[^>]+class="result__url"[^>]*>([\s\S]*?)</a>', block)
            if not title_match:
                title_match = re.search(r'<h2[^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)</a>', block)

            snippet_match = re.search(r'<a class="result__snippet"[^>]*>([\s\S]*?)</a>', block)

            raw_url = link_match.group(1) if link_match else ""
            clean_url = self._decode_duckduckgo_url(raw_url)

            # Strip HTML tags
            raw_title = title_match.group(1) if title_match else clean_url
            clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()

            raw_snippet = snippet_match.group(1) if snippet_match else ""
            clean_snippet = re.sub(r'<[^>]+>', '', raw_snippet).strip()

            if clean_url and clean_url.startswith("http"):
                # Derive readable domain
                parsed_uri = urllib.parse.urlparse(clean_url)
                domain = parsed_uri.netloc.replace("www.", "")
                results.append({
                    "title": clean_title or f"Source on {domain}",
                    "url": clean_url,
                    "domain": domain,
                    "snippet": clean_snippet,
                })
                if len(results) >= max_results:
                    break

        return results
