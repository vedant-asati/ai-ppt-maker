"""
source_analyzer.py — Pre-analyze source text before sending to the Planner.

Extracts key signals (stats, quotes, entities, key terms) that the Planner
should prioritize when building content_blocks.

This runs BEFORE the main planner call and injects a structured summary
as additional context — reducing hallucination and improving specificity.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class SourceSignals:
    """Structured analysis of source text signals."""
    word_count: int = 0
    sentence_count: int = 0
    stats: List[str] = field(default_factory=list)           # "400%", "$2.3B", "10x"
    quotes: List[str] = field(default_factory=list)          # "..." quoted text
    named_entities: List[str] = field(default_factory=list)  # Proper nouns
    key_terms: List[str] = field(default_factory=list)       # High-frequency nouns
    key_sentences: List[str] = field(default_factory=list)   # Topic sentences
    has_data_evidence: bool = False
    has_quotes: bool = False
    has_steps: bool = False    # Numbered lists, "step N", "first/second/third"
    has_comparison: bool = False
    estimated_slides: int = 0


class SourceAnalyzer:

    # ─── Regex patterns ──────────────────────────────────────────────────

    # Statistics: percentages, currencies, ratios, large numbers
    _STAT_PATTERN = re.compile(
        r"""
        (?:                          
            \$[\d,]+(?:\.\d+)?[KMBTkmbt]?  # Currency: $2.3B, $450,000
            | \d+(?:\.\d+)?[KMBTkmbt]?[%x×]  # Percentage or ratio: 40%, 10x
            | \d+(?:\.\d+)?x\b              # Multiplier: 3.5x
            | \d[\d,]{3,}                   # Large number: 10,000+
            | \b\d{1,3}(?:\.\d+)?           # Small precise number in context
              \s*(?:million|billion|trillion|thousand|percent)
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Quoted text
    _QUOTE_PATTERN = re.compile(
        r'["\u201c\u201d]([^"\u201c\u201d]{20,250})["\u201c\u201d]'
    )

    # Ordered list signals (numbered steps)
    _STEP_PATTERNS = [
        re.compile(r'^\s*\d+[\.\)]\s+\w', re.MULTILINE),
        re.compile(r'\b(?:first|second|third|fourth|fifth|step \d+|phase \d+)\b', re.IGNORECASE),
    ]

    # Comparison signals
    _COMPARISON_PATTERNS = [
        re.compile(r'\b(?:versus|vs\.?|compared to|in contrast|on the other hand|while|whereas)\b', re.IGNORECASE),
        re.compile(r'\b(?:traditional|conventional|old|new|modern|existing)\b', re.IGNORECASE),
    ]

    # Simple proper noun detection (capital letter words not starting sentences)
    _ENTITY_PATTERN = re.compile(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,3}\b')

    # Common English stopwords to exclude from key term extraction
    _STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
        'for', 'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'that', 'this', 'these',
        'those', 'it', 'its', 'they', 'their', 'we', 'our', 'you', 'your',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'each', 'more', 'also', 'as',
        'not', 'no', 'so', 'if', 'than', 'then', 'when', 'where', 'which',
        'how', 'what', 'who', 'any', 'all', 'both', 'most', 'other', 'some',
        'such', 'new', 'just', 'over', 'only', 'very', 'while',
    }

    def analyze(self, text: str) -> SourceSignals:
        """Run all analysis passes and return a SourceSignals object."""
        signals = SourceSignals()

        if not text or not text.strip():
            return signals

        # Basic counts
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        signals.word_count    = len(text.split())
        signals.sentence_count = len(sentences)

        # Stats extraction (filter out bare 4-digit calendar years 1900–2099)
        def _is_calendar_year(s: str) -> bool:
            cleaned = s.replace(',', '').strip()
            return cleaned.isdigit() and len(cleaned) == 4 and (1900 <= int(cleaned) <= 2099)

        stats_raw = self._STAT_PATTERN.findall(text)
        signals.stats = list(dict.fromkeys(s.strip() for s in stats_raw if not _is_calendar_year(s)))[:12]
        signals.has_data_evidence = len(signals.stats) >= 2

        # Quote extraction
        quotes_raw = self._QUOTE_PATTERN.findall(text)
        signals.quotes = [q.strip() for q in quotes_raw if len(q.strip()) >= 20][:4]
        signals.has_quotes = bool(signals.quotes)

        # Steps / numbered lists
        step_matches = sum(
            1 for pat in self._STEP_PATTERNS
            if pat.search(text)
        )
        signals.has_steps = step_matches >= 1

        # Comparison signals
        comp_matches = sum(
            len(pat.findall(text)) for pat in self._COMPARISON_PATTERNS
        )
        signals.has_comparison = comp_matches >= 1

        # Named entities (simple heuristic — capital words not after periods)
        sentences_lower = set(s[:2] for s in sentences if s)
        all_entities = self._ENTITY_PATTERN.findall(text)
        filtered = [
            e for e in all_entities
            if e not in sentences_lower and e.lower() not in self._STOPWORDS
        ]
        # Count frequency
        entity_freq: Dict[str, int] = {}
        for e in filtered:
            entity_freq[e] = entity_freq.get(e, 0) + 1
        signals.named_entities = sorted(
            entity_freq, key=lambda x: -entity_freq[x]
        )[:10]

        # Key terms (high-frequency nouns, length > 4)
        words = re.findall(r'\b[a-zA-Z]{5,}\b', text.lower())
        freq: Dict[str, int] = {}
        for w in words:
            if w not in self._STOPWORDS:
                freq[w] = freq.get(w, 0) + 1
        signals.key_terms = sorted(freq, key=lambda x: -freq[x])[:15]

        # Key sentences (first sentence of each paragraph = topic sentence)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for para in paragraphs[:8]:
            first_sent = (para.split('.')[0] + '.').strip()
            if 15 < len(first_sent) < 250:
                signals.key_sentences.append(first_sent)

        # Estimate slide count from content volume
        signals.estimated_slides = min(
            max(5, signals.word_count // 100),
            20
        )

        return signals

    def signals_for_prompt(self, signals: SourceSignals) -> str:
        """
        Return a formatted string injected into the Planner system prompt.
        Gives the AI a pre-analyzed view of the source material.
        """
        lines = [
            "SOURCE MATERIAL ANALYSIS:",
            f"  Word count: {signals.word_count} | Sentences: {signals.sentence_count}",
            f"  Suggested slide count: {signals.estimated_slides}",
            "",
        ]

        if signals.stats:
            lines.append("Key statistics found (USE THESE in StatBlock content_blocks):")
            for stat in signals.stats[:6]:
                lines.append(f"  • {stat}")
            lines.append("")

        if signals.quotes:
            lines.append("Notable quotes found (USE THESE in PullQuoteBlock content_blocks):")
            for q in signals.quotes[:2]:
                short_q = q[:150] + ("..." if len(q) > 150 else "")
                lines.append(f'  • "{short_q}"')
            lines.append("")

        if signals.named_entities:
            lines.append(f"Key entities: {', '.join(signals.named_entities[:6])}")

        if signals.key_terms:
            lines.append(f"Core topic vocabulary: {', '.join(signals.key_terms[:8])}")

        lines.append("")
        flags = []
        if signals.has_steps:         flags.append("has_steps → use StepBlock or timeline layout for process slides")
        if signals.has_comparison:    flags.append("has_comparison → use ComparisonBlock for contrast slide")
        if signals.has_data_evidence: flags.append("has_data → use StatBlock, include numbers in evidence slides")
        if signals.has_quotes:        flags.append("has_quotes → use PullQuoteBlock, consider 'quote' layout")

        if flags:
            lines.append("Content type signals:")
            for f in flags:
                lines.append(f"  → {f}")
            lines.append("")

        if signals.key_sentences:
            lines.append("Key topic sentences from source (use as inspiration, NOT verbatim):")
            for s in signals.key_sentences[:3]:
                lines.append(f"  • {s}")

        return "\n".join(lines)


def analyze_source(text: str) -> Optional[str]:
    """
    Convenience function: analyze text and return a prompt-ready string.
    Returns None if text is empty.
    """
    if not text or not text.strip():
        return None
    analyzer = SourceAnalyzer()
    signals = analyzer.analyze(text)
    return analyzer.signals_for_prompt(signals)
