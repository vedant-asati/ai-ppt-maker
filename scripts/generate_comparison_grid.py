"""
generate_comparison_grid.py — Renders high-fidelity slides across all 8 primary themes
and compiles a clean, modern 8-theme x 4-layout comparison grid for the repository documentation.
"""

import os
import sys
import tempfile
import time
from typing import List, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont

# Ensure project root is on path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from ppt_maker.core.schemas import (
    MasterPlan, Theme, Slide,
    KPIBlock, KPICard, StepBlock, StatBlock,
    ComparisonBlock, BentoBlock, BentoCard, Citation
)
from ppt_maker.design.theme_resolver import ThemeResolver
from ppt_maker.rendering.templater import Templater
from ppt_maker.rendering.renderer import Renderer


def get_font(size: int = 14, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def build_theme_plans() -> List[Dict]:
    """Build MasterPlans for the 8 primary visual styles, each with 4 distinct semantic layouts."""
    themes_def = [
        {
            "id": "corporate_clean",
            "name": "Corporate Clean",
            "palette": "executive_navy",
            "accent_hex": "#2563EB",
            "tag": "Enterprise Board & B2B",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="Enterprise Operating Review",
                    subtitle="Global Scalability & Fiscal 2027 Capital Strategy",
                    eyebrow="EXECUTIVE BRIEFING · Q4 2026"
                ),
                Slide(
                    slide_number=2,
                    layout_type="kpi_dashboard",
                    title="Core Financial & Operational Milestones",
                    subtitle="Top-decile unit economics across 4 operating dimensions",
                    content_blocks=[
                        KPIBlock(cards=[
                            KPICard(badge="ARR", value="$48.5M", label="Recurring Revenue", delta="+118% YoY"),
                            KPICard(badge="RETENTION", value="96.4%", label="Net Revenue Retention", delta="Top Decile"),
                            KPICard(badge="EFFICIENCY", value="3.4x", label="LTV:CAC Capital Ratio", delta="+0.8x YoY"),
                            KPICard(badge="MARGIN", value="78.2%", label="Non-GAAP Gross Margin", delta="+640 bps"),
                        ])
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="roadmap_chain",
                    title="Four-Phase Modernization Rollout",
                    subtitle="De-risked execution timeline aligned with tier-1 compliance",
                    content_blocks=[
                        StepBlock(
                            steps=[
                                "SOC2 Type II & FedRAMP Verification",
                                "Zero-Trust Database Isolation",
                                "EMEA Tier-1 Banking Go-Live",
                                "Autonomous Decision Workflows GA"
                            ],
                            step_labels=["Phase 1", "Phase 2", "Phase 3", "Phase 4"]
                        )
                    ]
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Tier-1 Enterprise Expansion",
                    subtitle="Rapid enterprise adoption across financial services",
                    content_blocks=[
                        StatBlock(
                            value="340%",
                            label="Year-over-Year Enterprise Account Volume",
                            context="42 Global Fortune 500 Institutions in Production"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="340% YoY expansion verified", source_title="S-1 Operating Benchmark", source_url="https://sec.gov", domain="sec.gov")
                    ]
                )
            ]
        },
        {
            "id": "dark_neon",
            "name": "Dark Neon",
            "palette": "cyber_cyan",
            "accent_hex": "#00FFD1",
            "tag": "Tech Pitch & Developer Keynotes",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="Autonomous Multi-Agent Architecture",
                    subtitle="Distributed Topology, Real-Time DOM Reflexion & Deterministic Guardrails",
                    eyebrow="SYSTEMS ARCHITECTURE · V4.2"
                ),
                Slide(
                    slide_number=2,
                    layout_type="bento",
                    title="Three-Tier Reflexion Architecture",
                    subtitle="Hierarchical error correction minimizing token burn and latency",
                    content_blocks=[
                        BentoBlock(
                            variant="bento_8_4",
                            cards=[
                                BentoCard(
                                    card_id="hero",
                                    card_style="elevated",
                                    title="Playwright CDP Telemetry Engine",
                                    body="Real-time DOM bounding box audit capturing overflow, occlusions, and contrast defects directly from Chromium.",
                                    badge="CDP Telemetry",
                                    stat_val="42ms",
                                    stat_label="P99 Telemetry"
                                ),
                                BentoCard(
                                    card_id="side_1",
                                    card_style="neutral",
                                    title="Tier 1 Micro-Fixer",
                                    body="0ms algorithmic line-height clamping and whitespace pruning.",
                                    badge="0ms Latency"
                                ),
                                BentoCard(
                                    card_id="side_2",
                                    card_style="neutral",
                                    title="Tier 2 Reflexion Critic",
                                    body="350-token surgical JSON patch via Gemini Flash Lite on failure.",
                                    badge="Targeted LLM"
                                ),
                            ]
                        )
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="split",
                    title="Architecture Paradigm Comparison",
                    subtitle="Moving from brittle prompting to closed-loop visual validation",
                    content_blocks=[
                        ComparisonBlock(
                            left_label="Single-Shot Prompting",
                            left_items=[
                                "No spatial awareness of rendered text boxes",
                                "Silent DOM text overflow and card clipping",
                                "Entire deck re-generation costs thousands of tokens"
                            ],
                            right_label="Agentic Verification Fabric",
                            right_items=[
                                "Playwright CDP real-time coordinate inspection",
                                "Algorithmic CSS line-height micro-adjustments",
                                "Targeted ~350-token localized JSON patches"
                            ]
                        )
                    ]
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="P99 Runtime Telemetry",
                    subtitle="Sub-50ms constraint resolution verified under high concurrency",
                    content_blocks=[
                        StatBlock(
                            value="42ms",
                            label="P99 Local Constraint Solving Latency",
                            context="Zero GPU starvation across 12,000 concurrent agent threads"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="42ms P99 latency verified", source_title="Agent Telemetry Log", source_url="https://ai.google.dev", domain="ai.google.dev")
                    ]
                )
            ]
        },
        {
            "id": "slidesgo_modern_proposal",
            "name": "SlidesGo Modern Proposal",
            "palette": "default",
            "accent_hex": "#D97706",
            "tag": "Client Pitches & Enterprise RFP",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="PulseFlow Series A Proposal",
                    subtitle="Enterprise Autonomous Telemetry & Edge Intelligence",
                    eyebrow="INVESTOR BRIEFING · SERIES A"
                ),
                Slide(
                    slide_number=2,
                    layout_type="kpi_dashboard",
                    title="Commercial Traction & Unit Economics",
                    subtitle="Sustained customer expansion across enterprise accounts",
                    content_blocks=[
                        KPIBlock(cards=[
                            KPICard(badge="ACV", value="$185k", label="Average Contract Value", delta="+42% YoY"),
                            KPICard(badge="EXPANSION", value="142%", label="Net Revenue Retention", delta="Top 1% SaaS"),
                            KPICard(badge="PIPELINE", value="$38M", label="Qualified Enterprise Pipeline", delta="3.8x Coverage"),
                            KPICard(badge="PAYBACK", value="8.5mo", label="CAC Payback Velocity", delta="-4.2mo YoY"),
                        ])
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="split",
                    title="Market Problem vs Autonomous Solution",
                    subtitle="Resolving enterprise telemetry fragmentation with unified intelligence",
                    content_blocks=[
                        ComparisonBlock(
                            left_label="Legacy Monitoring Stack",
                            left_items=[
                                "Fragmented telemetry silos across AWS, GCP, and on-prem",
                                "High false-alarm fatigue degrading SRE focus",
                                "Manual post-incident root cause investigations"
                            ],
                            right_label="PulseFlow Autonomous Fabric",
                            right_items=[
                                "Cross-cloud telemetry consolidated into single causal graph",
                                "Algorithmic alert deduplication cutting noise by 85%",
                                "Automated remediations resolving 70% of P1 incidents"
                            ]
                        )
                    ]
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Measurable Economic Return",
                    subtitle="Proven operational savings delivered within 90 days of rollout",
                    content_blocks=[
                        StatBlock(
                            value="12x",
                            label="Documented Enterprise Operational ROI",
                            context="1,400+ Engineering hours saved per quarter across 32 customers"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="12x ROI documented", source_title="Gartner Market Guide", source_url="https://gartner.com", domain="gartner.com")
                    ]
                )
            ]
        },
        {
            "id": "glassmorphism",
            "name": "Glassmorphism",
            "palette": "ocean_blue",
            "accent_hex": "#38BDF8",
            "tag": "SaaS & Modern UI/UX Showcases",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="Mastering Presentation Design",
                    subtitle="Design Tokens, Structural Layout Archetypes & Visual Hierarchy",
                    eyebrow="DESIGN SYSTEM · V4.2"
                ),
                Slide(
                    slide_number=2,
                    layout_type="kpi_dashboard",
                    title="System Engineering Metrics",
                    subtitle="Core capabilities of the presentation compiler",
                    content_blocks=[
                        KPIBlock(cards=[
                            KPICard(badge="LAYOUTS", value="14", label="Semantic Archetypes", delta="Bento, KPI, Split"),
                            KPICard(badge="THEMES", value="17", label="Managed Themes", delta="CSS Tokens"),
                            KPICard(badge="LATENCY", value="32ms", label="P99 Metric Audit", delta="Headless Playwright"),
                            KPICard(badge="BENCHMARK", value="96.4", label="Composite Score", delta="Grade A Baseline"),
                        ])
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="hero_statement",
                    title="Sub-50ms Constraint Resolution at Scale",
                    subtitle="Decoupled narrative planning, DOM inspection, and vector compilation delivers designer-grade presentations without manual tweaks.",
                    eyebrow="ARCHITECTURE ADVANTAGE"
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Empirical Evaluation Benchmark",
                    subtitle="Calibrated against 10 reference enterprise and research scenarios",
                    content_blocks=[
                        StatBlock(
                            value="96.4",
                            label="Composite Benchmark Evaluation Score",
                            context="100% Win rate against single-shot baseline generation"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="96.4 composite score", source_title="Multi-Agent Benchmark", source_url="https://github.com/vedant-asati/ai-ppt-maker", domain="github.com")
                    ]
                )
            ]
        },
        {
            "id": "editorial",
            "name": "Editorial",
            "palette": "parchment",
            "accent_hex": "#C4531F",
            "tag": "Thought Leadership & Industry Research",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="The Future of Generative Architecture",
                    subtitle="Cognitive Agents, Deterministic Bounds & Spatial Aesthetics",
                    eyebrow="THOUGHT LEADERSHIP · 2026"
                ),
                Slide(
                    slide_number=2,
                    layout_type="kpi_dashboard",
                    title="Macro Trends in Enterprise AI",
                    subtitle="Quantified shifts in engineering adoption and capital deployment",
                    content_blocks=[
                        KPIBlock(cards=[
                            KPICard(badge="ADOPTION", value="74%", label="Agentic Workflow GA", delta="+38% YoY"),
                            KPICard(badge="ACCURACY", value="99.2%", label="Deterministic Parsing", delta="Pydantic V2"),
                            KPICard(badge="TOKEN COST", value="-70%", label="Inference Optimization", delta="Flash Lite"),
                            KPICard(badge="RELIABILITY", value="99.9%", label="Constraint Adherence", delta="Zero Failures"),
                        ])
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="split",
                    title="Unconstrained vs Constrained Synthesis",
                    subtitle="Why spatial layout verification is essential for reliable AI design",
                    content_blocks=[
                        ComparisonBlock(
                            left_label="Unconstrained Single-Shot",
                            left_items=[
                                "Silent text clipping in browser rendering",
                                "Repetitive bullet lists and visual fatigue",
                                "Flat unstyled backgrounds without tactile depth"
                            ],
                            right_label="Constrained Multi-Stage Pipeline",
                            right_items=[
                                "Pydantic V2 schema validation and slot budgets",
                                "Jinja2 design token binding and CSS palettes",
                                "Real-time Playwright CDP DOM overflow detection"
                            ]
                        )
                    ]
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Reliability Verification Rate",
                    subtitle="Deterministic structural adherence across automated test suites",
                    content_blocks=[
                        StatBlock(
                            value="99.9%",
                            label="Automated Constraint Adherence Rate",
                            context="Zero layout clipping across 25,000 benchmark slide generations"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="99.9% adherence rate verified", source_title="Evaluation Audit Report", source_url="https://ai.google.dev", domain="ai.google.dev")
                    ]
                )
            ]
        },
        {
            "id": "slidesgo_creative_watercolor",
            "name": "Creative Watercolor",
            "palette": "default",
            "accent_hex": "#2563EB",
            "tag": "Creative Portfolios & Studio Pitches",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="Studio Art & Design Direction",
                    subtitle="Organic Textures, Tactile Paper Grains & Visual Rhythm",
                    eyebrow="CREATIVE PORTFOLIO · 2026"
                ),
                Slide(
                    slide_number=2,
                    layout_type="kpi_dashboard",
                    title="Creative Direction Metrics",
                    subtitle="Audience engagement and aesthetic benchmark scores",
                    content_blocks=[
                        KPIBlock(cards=[
                            KPICard(badge="TEXTURE", value="Cold-Press", label="Authentic Paper Grain", delta="Tactile Feel"),
                            KPICard(badge="HARMONY", value="94.2", label="Palette Cohesion Index", delta="Cobalt & Ochre"),
                            KPICard(badge="DIVERSITY", value="85%", label="Asymmetric Archetypes", delta="Zero Bullet Slop"),
                            KPICard(badge="RECALL", value="+40%", label="Viewer Brand Recall", delta="vs Flat Decks"),
                        ])
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="roadmap_chain",
                    title="Four-Stage Creative Process",
                    subtitle="From conceptual moodboard to textured presentation export",
                    content_blocks=[
                        StepBlock(
                            steps=[
                                "Concept & Narrative Blueprinting",
                                "Tactile Texture & Palette Selection",
                                "Asymmetric Layout Composition",
                                "Dual Vector PDF & Native PPTX Export"
                            ],
                            step_labels=["Stage 1", "Stage 2", "Stage 3", "Stage 4"]
                        )
                    ]
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Enhanced Audience Recall",
                    subtitle="Presentations with authentic textures drive higher cognitive impact",
                    content_blocks=[
                        StatBlock(
                            value="+40%",
                            label="Improvement in Post-Meeting Content Recall",
                            context="Measured across 120 blind participant evaluations"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="+40% recall improvement", source_title="Cognitive Design Journal", source_url="https://design.org", domain="design.org")
                    ]
                )
            ]
        },
        {
            "id": "slidesgo_dark_tech",
            "name": "SlidesGo Dark Tech",
            "palette": "default",
            "accent_hex": "#06B6D4",
            "tag": "Deep Tech & Infrastructure Systems",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="Deep Tech & Silicon Acceleration",
                    subtitle="Heterogeneous Compute, Vector Engines & Real-Time Kernels",
                    eyebrow="TECHNICAL ARCHITECTURE"
                ),
                Slide(
                    slide_number=2,
                    layout_type="bento",
                    title="Hardware Accelerator Subsystems",
                    subtitle="High-bandwidth interconnect and specialized matrix compute",
                    content_blocks=[
                        BentoBlock(
                            variant="bento_8_4",
                            cards=[
                                BentoCard(
                                    card_id="hero",
                                    card_style="elevated",
                                    title="Tensor Matrix Vector Core",
                                    body="Optimized silicon execution pipeline delivering 128 Teraflops with hardware-enforced memory bounds.",
                                    badge="Matrix Compute",
                                    stat_val="128 TF",
                                    stat_label="FP16 Compute"
                                ),
                                BentoCard(
                                    card_id="side_1",
                                    card_style="neutral",
                                    title="Ultra-Bandwidth Crossbar",
                                    body="2.4 TB/s direct die-to-die memory interface.",
                                    badge="2.4 TB/s"
                                ),
                                BentoCard(
                                    card_id="side_2",
                                    card_style="neutral",
                                    title="Deterministic Scheduler",
                                    body="Sub-microsecond kernel synchronization.",
                                    badge="Zero Jitter"
                                ),
                            ]
                        )
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="split",
                    title="Monolith vs Distributed Accelerators",
                    subtitle="Architectural transition to heterogeneous compute fabrics",
                    content_blocks=[
                        ComparisonBlock(
                            left_label="Centralized Monolith",
                            left_items=[
                                "High memory bus contention bottlenecks",
                                "Unpredictable tail latency spikes under load",
                                "Rigid single-node hardware boundaries"
                            ],
                            right_label="Distributed Compute Fabric",
                            right_items=[
                                "Elastic multi-die interconnect scaling",
                                "Sub-millisecond lock-free synchronization",
                                "Dynamic task rebalancing across clusters"
                            ]
                        )
                    ]
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Distributed Compute Acceleration",
                    subtitle="Empirically verified throughput speedup over baseline servers",
                    content_blocks=[
                        StatBlock(
                            value="4.8x",
                            label="Sustained Training & Inference Speedup",
                            context="Benchmarked across 64-node distributed cluster"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="4.8x speedup benchmarked", source_title="MLSys Systems Conference", source_url="https://mlsys.org", domain="mlsys.org")
                    ]
                )
            ]
        },
        {
            "id": "aurora",
            "name": "Aurora",
            "palette": "cosmic",
            "accent_hex": "#8B5CF6",
            "tag": "AI Platforms & Keynotes",
            "slides": [
                Slide(
                    slide_number=1,
                    layout_type="cover",
                    title="Frontier Foundation Models",
                    subtitle="Neural Scaling, Multimodal Reasoning & Agentic Workflows",
                    eyebrow="RESEARCH KEYNOTE · 2026"
                ),
                Slide(
                    slide_number=2,
                    layout_type="kpi_dashboard",
                    title="Frontier Intelligence Dimensions",
                    subtitle="Evaluation metrics across multimodal reasoning tasks",
                    content_blocks=[
                        KPIBlock(cards=[
                            KPICard(badge="SCALE", value="2.4T", label="Parameter MoE Scale", delta="Sparse Routing"),
                            KPICard(badge="THROUGHPUT", value="14.2B", label="Daily Tokens Processed", delta="+240% YoY"),
                            KPICard(badge="BENCHMARK", value="98.6%", label="Multi-Turn Reasoning", delta="Frontier State"),
                            KPICard(badge="EFFICIENCY", value="3.2x", label="FLOPs per Watt Energy", delta="Green Compute"),
                        ])
                    ]
                ),
                Slide(
                    slide_number=3,
                    layout_type="hero_statement",
                    title="Unified Multimodal Reasoning Across Modalities",
                    subtitle="Fluid cross-attention architectures enable joint spatial, textual, and programmatic reasoning in real time with zero modality barriers.",
                    eyebrow="RESEARCH BREAKTHROUGH"
                ),
                Slide(
                    slide_number=4,
                    layout_type="stat",
                    title="Massive Long-Horizon Context",
                    subtitle="Full document archive synthesis without retrieval degradation",
                    content_blocks=[
                        StatBlock(
                            value="840B",
                            label="Pre-Trained Active Context Window",
                            context="Zero perplexity degradation over 1,000,000 token documents"
                        )
                    ],
                    citations=[
                        Citation(id=1, claim="840B context window verified", source_title="NeurIPS Proceedings", source_url="https://nips.cc", domain="nips.cc")
                    ]
                )
            ]
        },
    ]
    return themes_def


def generate_all_slides_and_build_grid():
    output_grid_path = os.path.join(ROOT_DIR, "docs", "assets", "comparison_grid.png")
    os.makedirs(os.path.dirname(output_grid_path), exist_ok=True)

    themes_def = build_theme_plans()
    n_themes = len(themes_def)
    n_cols = 4  # Cover, KPI/Bento Scorecard, Strategic Split/Roadmap, Stat Callout

    print(f"Generating 8-theme comparison grid ({n_themes} themes x {n_cols} slides = {n_themes * n_cols} slides)...")
    t0 = time.time()

    rendered_images: Dict[str, List[Image.Image]] = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        for idx, t_info in enumerate(themes_def, 1):
            sc = t_info["id"]
            pal = t_info["palette"]
            print(f"[{idx}/{n_themes}] Templating & rendering theme: {t_info['name']} ({sc} / {pal})...")

            css_vars, _ = ThemeResolver.resolve(structural_class=sc, palette_name=pal, ai_css_vars={})
            theme = Theme(structural_class=sc, palette=pal, css_variables=css_vars)
            plan = MasterPlan(theme=theme, slides=t_info["slides"])

            theme_dir = os.path.join(tmp_dir, sc)
            os.makedirs(theme_dir, exist_ok=True)

            templater = Templater(build_dir=theme_dir)
            html_files = templater.generate_html(plan)

            renderer = Renderer(build_dir=theme_dir)
            png_files, _ = renderer.render_all(html_files)

            # Load images into memory
            rendered_images[sc] = [Image.open(f).copy() for f in png_files]

    print(f"All 32 slides rendered successfully in {time.time() - t0:.2f}s!")

    # ─── Composite Comparison Grid ──────────────────────────────────────────
    print("Compositing high-resolution visual comparison grid...")
    thumb_w = 560
    thumb_h = 315  # exact 16:9
    gap_x = 16
    gap_y = 20
    sidebar_w = 260
    header_h = 130
    margin = 32

    total_w = margin * 2 + sidebar_w + (thumb_w * n_cols) + (gap_x * (n_cols - 1))
    total_h = margin * 2 + header_h + (thumb_h * n_themes) + (gap_y * (n_themes - 1))

    # Dark executive canvas matching GitHub dark mode
    canvas = Image.new("RGB", (total_w, total_h), color="#0B0F17")
    draw = ImageDraw.Draw(canvas)

    font_title = get_font(28, bold=True)
    font_sub = get_font(15, bold=False)
    font_col_hd = get_font(13, bold=True)
    font_theme_name = get_font(17, bold=True)
    font_theme_tag = get_font(12, bold=False)
    font_theme_sub = get_font(11, bold=False)

    # 1. Header Zone
    draw.text((margin, margin + 4), "VISUAL THEMES & SEMANTIC LAYOUT COMPARISON", fill="#F8FAFC", font=font_title)
    draw.text((margin, margin + 44), "Declarative Design Tokens · Authentic Tactile Textures · Dynamic Presentation Archetypes (V4.2)", fill="#94A3B8", font=font_sub)

    # Subtle header divider
    draw.line([(margin, margin + 74), (total_w - margin, margin + 74)], fill="#1E293B", width=1)

    # Column Labels
    col_labels = [
        "01 · ARCHITECTURAL COVER",
        "02 · DATA & KPI SCORECARD",
        "03 · ASYMMETRIC SPLIT & ROADMAP",
        "04 · STAT CALLOUT & CITATION"
    ]
    for c_idx, label in enumerate(col_labels):
        x = margin + sidebar_w + (c_idx * (thumb_w + gap_x))
        draw.text((x + 4, margin + 92), label, fill="#64748B", font=font_col_hd)

    # 2. Render Each Theme Row
    for r_idx, t_info in enumerate(themes_def):
        sc = t_info["id"]
        y = margin + header_h + (r_idx * (thumb_h + gap_y))

        # Theme Sidebar Card
        sidebar_card_x1 = margin
        sidebar_card_y1 = y
        sidebar_card_x2 = margin + sidebar_w - 20
        sidebar_card_y2 = y + thumb_h

        # Sidebar background pill
        draw.rounded_rectangle(
            [(sidebar_card_x1, sidebar_card_y1), (sidebar_card_x2, sidebar_card_y2)],
            radius=12,
            fill="#111827",
            outline="#1F2937",
            width=1
        )

        # Theme accent color strip on left edge
        accent_color = t_info["accent_hex"]
        draw.rounded_rectangle(
            [(sidebar_card_x1 + 4, sidebar_card_y1 + 14), (sidebar_card_x1 + 8, sidebar_card_y2 - 14)],
            radius=2,
            fill=accent_color
        )

        # Theme text
        tx = sidebar_card_x1 + 22
        draw.text((tx, sidebar_card_y1 + 24), t_info["name"].upper(), fill="#F1F5F9", font=font_theme_name)
        draw.text((tx, sidebar_card_y1 + 54), t_info["tag"], fill="#94A3B8", font=font_theme_tag)

        # Metadata pill: palette + structural class
        pal_text = f"palette: {t_info['palette']}"
        draw.text((tx, sidebar_card_y1 + 84), f"`{sc}`", fill=accent_color, font=font_theme_sub)
        draw.text((tx, sidebar_card_y1 + 104), pal_text, fill="#64748B", font=font_theme_sub)

        # 4 Slide Thumbnails
        theme_slides = rendered_images.get(sc, [])
        for c_idx in range(n_cols):
            x = margin + sidebar_w + (c_idx * (thumb_w + gap_x))
            if c_idx < len(theme_slides):
                slide_im = theme_slides[c_idx]
                thumb = slide_im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas.paste(thumb, (x, y))

                # Subtle 1px frame border around thumbnail
                draw.rectangle([(x, y), (x + thumb_w - 1, y + thumb_h - 1)], outline="#1E293B", width=1)

    # Save final comparison grid
    canvas.save(output_grid_path, "PNG", optimize=True)
    print(f"\n=======================================================")
    print(f"Successfully generated comparison grid: {output_grid_path}")
    print(f"Dimensions: {canvas.size[0]}x{canvas.size[1]} | File Size: {os.path.getsize(output_grid_path) // 1024} KB")
    print(f"=======================================================")


if __name__ == "__main__":
    generate_all_slides_and_build_grid()
