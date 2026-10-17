"""
agent.py — Grounded Research Agent orchestrator.

Coordinates QueryDecomposer, DuckDuckGo search retrieval, HTML extraction,
and grounded claim synthesis with robust fallback degradation.
"""

import os
from typing import List, Dict, Any, Optional

try:
    from ppt_maker.core.schemas import Citation
    from ppt_maker.research.searcher import QueryDecomposer, DuckDuckGoSearchProvider
    from ppt_maker.research.synthesizer import ResearchSynthesizer, GroundedBrief
except ImportError:
    from schemas import Citation
    from searcher import QueryDecomposer, DuckDuckGoSearchProvider
    from synthesizer import ResearchSynthesizer, GroundedBrief


class ResearchAgent:
    """
    Autonomous research agent for topic-driven presentation planning.
    Expands the agency from a file converter into a grounded presentation creator.
    """

    def __init__(
        self,
        search_provider=None,
        decomposer=None,
        synthesizer=None,
        client=None,
    ):
        self.client = client
        self.search_provider = search_provider or DuckDuckGoSearchProvider()
        self.decomposer = decomposer or QueryDecomposer(client=client)
        self.synthesizer = synthesizer or ResearchSynthesizer(client=client)

    def conduct_research(
        self,
        topic: str,
        max_sources_per_query: int = 2,
        total_sources_cap: int = 6
    ) -> GroundedBrief:
        """
        Executes end-to-end research:
          1. Query decomposition (3 focused sub-queries)
          2. Web discovery via DuckDuckGo
          3. Deduplication and snippet extraction
          4. Grounded synthesis into GroundedBrief
          5. Transparent fallback if web search is offline
        """
        clean_topic = topic.strip()
        print(f"ResearchAgent: Initiating grounded research on '{clean_topic}'...")

        # 1. Decompose into 3 angles
        sub_queries = self.decomposer.decompose(clean_topic)
        print(f"  [Research] Decomposed into {len(sub_queries)} angles:")
        for q in sub_queries:
            print(f"    • {q}")

        # 2. Retrieve search results
        collected_sources: List[Dict[str, str]] = []
        seen_urls = set()

        try:
            for q in sub_queries:
                results = self.search_provider.search(q, max_results=max_sources_per_query)
                for r in results:
                    url = r.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        collected_sources.append(r)
                        if len(collected_sources) >= total_sources_cap:
                            break
                if len(collected_sources) >= total_sources_cap:
                    break
        except Exception as e:
            print(f"  [Notice] Web search encountered an issue: {e}")

        # 3. Check if search succeeded or fallback required
        if collected_sources:
            print(f"  [Research] Discovered {len(collected_sources)} unique verified source(s).")
            brief = self.synthesizer.synthesize(clean_topic, collected_sources, client=self.client)
            return brief

        # 4. Graceful degradation fallback
        print("  [Notice] Web search returned 0 sources. Activating baseline knowledge fallback.")
        fallback_summary = (
            f"Autonomous briefing on {clean_topic} derived from baseline model knowledge. "
            f"Synthesizes established architectural, technical, and industry fundamentals."
        )
        return GroundedBrief(
            topic=clean_topic,
            summary=fallback_summary,
            facts=[
                {"claim": f"Core principles and technological evolution underlying {clean_topic}.", "citation_id": 1},
                {"claim": f"Key industry drivers and performance trade-offs in {clean_topic}.", "citation_id": 2},
            ],
            sources=[],
            citations=[],
            suggested_narrative="Market Context & Motivation -> Technical Architecture & Trade-offs -> Strategic Outlook",
            is_fallback=True,
            disclaimer_banner="⚠️ Generated from AI baseline knowledge — web search verification offline.",
        )
