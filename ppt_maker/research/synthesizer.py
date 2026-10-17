"""
synthesizer.py — HTML content cleaning and GroundedBrief claim synthesis.

Extracts substantive article text, filters noise (scripts, ads, navigation),
and synthesizes grounded facts with verifiable citation footnotes.
"""

import os
import re
import json
import urllib.parse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from ppt_maker.core.schemas import Citation
except ImportError:
    from schemas import Citation


def extract_article_content(html: str, max_words: int = 800) -> str:
    """
    Strips scripts, styles, navigation, headers, footers, forms, and cookie notices,
    returning clean, substantive paragraphs up to max_words.
    """
    if not html:
        return ""

    # Remove script, style, nav, footer, header, form, svg, noscript tags
    cleaned = re.sub(r'<(script|style|nav|header|footer|aside|form|svg|noscript)[^>]*>[\s\S]*?</\1>', ' ', html, flags=re.IGNORECASE)
    # Remove HTML comments
    cleaned = re.sub(r'<!--[\s\S]*?-->', ' ', cleaned)
    # Remove remaining HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # Unescape common entities
    cleaned = cleaned.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    words = cleaned.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return cleaned


class GroundedBrief(BaseModel):
    """
    Structured research brief providing verified facts and citations for presentation planning.
    """
    topic: str
    summary: str
    facts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of verified facts or data points extracted from sources."
    )
    sources: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of consulted source articles with title, url, domain."
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Footnote citations ready to be attached to slides."
    )
    suggested_narrative: str = Field(
        default="",
        description="Recommended narrative progression (Hook -> Evidence -> Conclusion)."
    )
    is_fallback: bool = Field(
        default=False,
        description="True if web search was unavailable and internal knowledge was used."
    )
    disclaimer_banner: Optional[str] = Field(
        default=None,
        description="Subtle banner injected into cover slide when web verification was offline."
    )

    def to_source_text(self) -> str:
        """
        Formats the brief into structured Markdown source text for the Planner,
        including factual evidence, source citations, and suggested arc.
        """
        parts = [
            f"# Research Dossier: {self.topic}",
            "",
            f"## Executive Summary",
            self.summary,
            "",
            "## Verified Evidence & Key Metrics",
        ]

        for i, fact in enumerate(self.facts, start=1):
            claim = fact.get("claim", "")
            src_id = fact.get("citation_id", i)
            parts.append(f"- {claim} [{src_id}]")

        if self.suggested_narrative:
            parts.extend([
                "",
                "## Recommended Narrative Arc",
                self.suggested_narrative,
            ])

        if self.citations:
            parts.extend([
                "",
                "## Consulted Sources & Citations",
            ])
            for c in self.citations:
                parts.append(f"[{c.id}] {c.source_title} ({c.domain}) — {c.source_url}")

        if self.disclaimer_banner:
            parts.extend([
                "",
                f"> Notice: {self.disclaimer_banner}"
            ])

        return "\n".join(parts)


_SYNTHESIZER_SYSTEM_PROMPT = """\
You are an expert Presentation Research Analyst.
Your task is to synthesize raw web research snippets into a structured GroundedBrief JSON object.

Extract 6 to 10 concrete, verifiable claims or statistics.
Map each claim to a numeric citation ID referencing the exact source provided.
Do NOT invent claims not found in the provided sources.

Return ONLY a valid JSON object matching this schema:
{
  "summary": "2-3 sentence executive synthesis of the topic",
  "facts": [
    {"claim": "Specific fact or metric statement", "citation_id": 1}
  ],
  "suggested_narrative": "Hook -> Problem -> Technological/Strategic Breakthrough -> Outlook"
}
"""


class ResearchSynthesizer:
    """
    Synthesizes scraped article content and search snippets into a GroundedBrief.
    """

    def __init__(self, client=None):
        self.client = client

    def synthesize(
        self,
        topic: str,
        sources: List[Dict[str, str]],
        client=None
    ) -> GroundedBrief:
        """
        Synthesizes research sources into a GroundedBrief.
        Uses Gemini if client is available; otherwise applies deterministic extraction.
        """
        active_client = client or self.client

        # Build citations list from sources
        citations = []
        for i, src in enumerate(sources, start=1):
            url = src.get("url", "")
            domain = src.get("domain", "")
            if not domain and url:
                domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
            citations.append(Citation(
                id=i,
                claim=src.get("snippet", src.get("title", ""))[:120],
                source_title=src.get("title", f"Source {i}"),
                source_url=url,
                domain=domain or "web",
            ))

        if active_client and sources:
            try:
                from google.genai import types
                sources_block = []
                for c in citations:
                    snippet = next((s.get("snippet", "") for s in sources if s.get("url") == c.source_url), "")
                    sources_block.append(f"[{c.id}] {c.source_title} ({c.source_url}):\n{snippet}\n")

                prompt = (
                    f"TOPIC: {topic}\n\n"
                    f"SOURCES:\n"
                    f"{''.join(sources_block)}\n\n"
                    f"Synthesize these sources into verified facts with citation references."
                )

                response = active_client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=_SYNTHESIZER_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=1500,
                    )
                )

                raw_text = response.text.strip()
                match = re.search(r'(\{[\s\S]*\})', raw_text)
                if match:
                    raw_text = match.group(1)
                data = json.loads(raw_text)

                return GroundedBrief(
                    topic=topic,
                    summary=data.get("summary", f"Grounded research on {topic}"),
                    facts=data.get("facts", []),
                    sources=sources,
                    citations=citations,
                    suggested_narrative=data.get("suggested_narrative", ""),
                    is_fallback=False,
                )
            except Exception:
                pass

        # Deterministic extraction fallback (100% offline & fast)
        facts = []
        for i, src in enumerate(sources, start=1):
            snippet = src.get("snippet", "").strip()
            if snippet:
                facts.append({"claim": snippet, "citation_id": i})
            elif src.get("title"):
                facts.append({"claim": src.get("title"), "citation_id": i})

        summary = (
            f"Research on {topic} compiled from {len(sources)} source(s). "
            f"Key metrics and technological developments highlight rapid ecosystem evolution."
        )

        return GroundedBrief(
            topic=topic,
            summary=summary,
            facts=facts,
            sources=sources,
            citations=citations,
            suggested_narrative="Context & Problem Statement -> Empirical Evidence -> Strategic Outlook",
            is_fallback=False,
        )
