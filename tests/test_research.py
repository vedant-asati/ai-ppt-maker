"""
test_research.py — Unit tests for Grounded Research Agent (Phase 4).

Validates:
1. QueryDecomposer produces 3 orthogonal angles (rule-based fallback & mock client).
2. HTML article text extraction cleanly strips boilerplate (nav, scripts, ads, cookies).
3. DuckDuckGo redirect URL decoding and domain extraction.
4. GroundedBrief structured dossier formatting and citation footnote generation.
5. ResearchSynthesizer claim extraction and citation attachment.
6. ResearchAgent end-to-end research flow with injected MockSearchProvider.
7. Graceful degradation: network failure falls back to internal knowledge with disclaimer banner.
8. Citation model integration with Slide schema.
"""

import os
import json
import unittest
from unittest.mock import MagicMock
from ppt_maker.core.schemas import Citation, Slide, Theme, MasterPlan
from ppt_maker.research.searcher import QueryDecomposer, DuckDuckGoSearchProvider
from ppt_maker.research.synthesizer import (
    extract_article_content,
    GroundedBrief,
    ResearchSynthesizer,
)
from ppt_maker.research.agent import ResearchAgent


class MockSearchProvider:
    """Mock search provider for fast, deterministic, 100% offline tests."""

    def __init__(self, should_fail: bool = False, empty: bool = False):
        self.should_fail = should_fail
        self.empty = empty
        self.queries_received = []

    def search(self, query: str, max_results: int = 2):
        self.queries_received.append(query)
        if self.should_fail:
            raise ConnectionError("Simulated DuckDuckGo connection timeout")
        if self.empty:
            return []
        return [
            {
                "title": f"Scientific Review on {query[:30]}",
                "url": f"https://nature.com/articles/research-{len(self.queries_received)}",
                "domain": "nature.com",
                "snippet": f"Empirical findings demonstrate 450 Wh/kg energy density under lab conditions for {query[:20]}.",
            },
            {
                "title": f"Market Outlook: {query[:30]}",
                "url": f"https://reuters.com/business/tech-{len(self.queries_received)}",
                "domain": "reuters.com",
                "snippet": f"Global investment reached $4.2B in 2025 across key battery consortiums.",
            }
        ]


class TestResearchAgent(unittest.TestCase):

    def test_01_query_decomposer_rule_based(self):
        """Verify rule-based fallback produces 3 distinct query angles."""
        decomposer = QueryDecomposer(client=None)
        queries = decomposer.decompose("Solid-State Batteries")
        self.assertEqual(len(queries), 3)
        self.assertIn("overview", queries[0].lower())
        self.assertIn("challenges", queries[1].lower())
        self.assertIn("projections", queries[2].lower())

    def test_02_query_decomposer_with_mock_client(self):
        """Verify query decomposer with mock LLM client."""
        mock_resp = MagicMock()
        mock_resp.text = json.dumps([
            "solid state battery commercial breakthroughs 2026",
            "dendrite prevention solid electrolyte interface challenges",
            "automotive solid state battery cost parity timeline"
        ])
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp

        decomposer = QueryDecomposer(client=mock_client)
        queries = decomposer.decompose("Solid-State Batteries")

        self.assertEqual(len(queries), 3)
        self.assertIn("breakthroughs", queries[0])
        self.assertIn("dendrite", queries[1])
        mock_client.models.generate_content.assert_called_once()

    def test_03_extract_article_content_filters_noise(self):
        """Verify HTML extractor strips scripts, styles, navs, footers, and cookie banners."""
        raw_html = """
        <!DOCTYPE html>
        <html>
        <head>
          <script>console.log("analytics tracking code");</script>
          <style>body { font-size: 14px; }</style>
        </head>
        <body>
          <header><nav><a href="/">Home</a><a href="/pricing">Pricing</a></nav></header>
          <aside><div class="cookie-banner">Accept all tracking cookies?</div></aside>
          <main>
            <h1>Solid-State Breakthrough</h1>
            <p>Researchers at QuantumScape achieved 800 continuous cycles with 95% capacity retention.</p>
            <p>Commercial deployment in electric vehicles is projected for late 2026.</p>
          </main>
          <footer><p>&copy; 2026 TechMedia Inc. All rights reserved.</p></footer>
        </body>
        </html>
        """
        extracted = extract_article_content(raw_html, max_words=50)

        self.assertNotIn("analytics tracking code", extracted)
        self.assertNotIn("Accept all tracking cookies", extracted)
        self.assertNotIn("Pricing", extracted)
        self.assertNotIn("All rights reserved", extracted)
        self.assertIn("Solid-State Breakthrough", extracted)
        self.assertIn("800 continuous cycles", extracted)
        self.assertIn("late 2026", extracted)

    def test_04_duckduckgo_url_decoding(self):
        """Verify decoding of DuckDuckGo redirect URLs."""
        raw = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.nature.com%2Farticles%2Fs41586-026-001&rut=xyz"
        decoded = DuckDuckGoSearchProvider._decode_duckduckgo_url(raw)
        self.assertEqual(decoded, "https://www.nature.com/articles/s41586-026-001")

        direct = "https://bloomberg.com/news/articles/2026-01-15/solid-state"
        self.assertEqual(DuckDuckGoSearchProvider._decode_duckduckgo_url(direct), direct)

    def test_05_grounded_brief_formatting_and_citations(self):
        """Verify GroundedBrief produces structured markdown dossier with citations."""
        citations = [
            Citation(id=1, claim="Energy density reached 450 Wh/kg", source_title="Nature Energy", source_url="https://nature.com/articles/1", domain="nature.com"),
            Citation(id=2, claim="Consortium funding reached $4.2B", source_title="Reuters", source_url="https://reuters.com/tech/1", domain="reuters.com"),
        ]
        brief = GroundedBrief(
            topic="Solid-State Battery Progress",
            summary="Solid-state batteries represent the next frontier in EV energy storage.",
            facts=[
                {"claim": "Energy density reached 450 Wh/kg in testing", "citation_id": 1},
                {"claim": "Total global consortium funding reached $4.2B", "citation_id": 2},
            ],
            citations=citations,
            suggested_narrative="Hook -> Technological Hurdles -> Commercial Timelines",
        )

        dossier = brief.to_source_text()
        self.assertIn("# Research Dossier: Solid-State Battery Progress", dossier)
        self.assertIn("## Executive Summary", dossier)
        self.assertIn("Energy density reached 450 Wh/kg in testing [1]", dossier)
        self.assertIn("[1] Nature Energy (nature.com) — https://nature.com/articles/1", dossier)
        self.assertIn("[2] Reuters (reuters.com) — https://reuters.com/tech/1", dossier)

    def test_06_research_synthesizer_with_mock_client(self):
        """Verify ResearchSynthesizer maps raw sources to GroundedBrief with mock LLM."""
        sources = [
            {"title": "Breakthrough Paper", "url": "https://science.org/paper1", "domain": "science.org", "snippet": "Cathode stability reached 1000 cycles."},
            {"title": "Industry Review", "url": "https://ieee.org/review", "domain": "ieee.org", "snippet": "Cost per kWh expected to reach $75 by 2028."}
        ]

        mock_llm_json = """{
            "summary": "Solid-state technology demonstrates unprecedented cycle life and cost reduction trajectories.",
            "facts": [
                {"claim": "Cathode stability demonstrated 1,000 cycles at room temperature", "citation_id": 1},
                {"claim": "Pack-level cost parity of $75/kWh forecasted for 2028", "citation_id": 2}
            ],
            "suggested_narrative": "Status Quo -> Cathode Stability -> Cost Parity by 2028"
        }"""
        mock_resp = MagicMock()
        mock_resp.text = mock_llm_json
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp

        synthesizer = ResearchSynthesizer(client=mock_client)
        brief = synthesizer.synthesize("Battery Chemistries", sources)

        self.assertFalse(brief.is_fallback)
        self.assertEqual(len(brief.citations), 2)
        self.assertEqual(len(brief.facts), 2)
        self.assertIn("Cathode stability", brief.facts[0]["claim"])
        self.assertEqual(brief.citations[0].domain, "science.org")

    def test_07_research_agent_end_to_end_with_mock_provider(self):
        """Verify full ResearchAgent pipeline with MockSearchProvider."""
        mock_search = MockSearchProvider()
        agent = ResearchAgent(search_provider=mock_search)

        brief = agent.conduct_research("Next-Gen Fusion Energy", max_sources_per_query=2)

        self.assertFalse(brief.is_fallback)
        self.assertGreaterEqual(len(brief.citations), 2)
        self.assertIn("Next-Gen Fusion Energy", brief.topic)
        # Verify 3 decomposed queries were executed
        self.assertEqual(len(mock_search.queries_received), 3)

    def test_08_research_agent_graceful_degradation_on_failure(self):
        """Verify that when web search fails, ResearchAgent degrades gracefully with disclaimer banner."""
        failing_search = MockSearchProvider(should_fail=True)
        agent = ResearchAgent(search_provider=failing_search)

        brief = agent.conduct_research("Offline Edge Case Topic")

        self.assertTrue(brief.is_fallback)
        self.assertEqual(len(brief.citations), 0)
        self.assertIsNotNone(brief.disclaimer_banner)
        self.assertIn("baseline knowledge", brief.disclaimer_banner)

        # Ensure to_source_text contains disclaimer notice
        dossier = brief.to_source_text()
        self.assertIn("Notice:", dossier)

    def test_09_citation_schema_and_slide_integration(self):
        """Verify Citation model contract and compatibility with Slide schema."""
        citation = Citation(
            id=1,
            claim="Energy efficiency improved by 40%",
            source_title="Energy Journal 2026",
            source_url="https://energy.org/2026",
            domain="energy.org"
        )
        slide = Slide(
            slide_number=2,
            layout_type="stat",
            title="40% Efficiency Gains",
            citations=[citation],
            eyebrow_banner="Verified Source"
        )

        self.assertEqual(len(slide.citations), 1)
        self.assertEqual(slide.citations[0].domain, "energy.org")
        self.assertEqual(slide.eyebrow_banner, "Verified Source")

        # MasterPlan JSON round-trip
        theme = Theme(structural_class="corporate_clean", palette="executive_navy")
        mp = MasterPlan(theme=theme, slides=[slide])
        json_str = mp.model_dump_json()
        mp_restored = MasterPlan.model_validate_json(json_str)

        self.assertEqual(len(mp_restored.slides[0].citations), 1)
        self.assertEqual(mp_restored.slides[0].citations[0].claim, "Energy efficiency improved by 40%")


if __name__ == "__main__":
    unittest.main()
