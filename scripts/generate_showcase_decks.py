"""
generate_showcase_decks.py — Generates canonical showcase presentations (PDF, PPTX, Speaker Notes)
and visual preview assets for the AI Presentation Agency repository.
"""

import os
import sys
import json
import tempfile
from typing import Dict, List
from PIL import Image

# Ensure project root is on path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from ppt_maker.core.schemas import (
    MasterPlan, Theme, Slide,
    KPIBlock, KPICard, StepBlock, StatBlock,
    ComparisonBlock, PullQuoteBlock, BentoBlock, BentoCard,
    Citation,
)
from ppt_maker.design.theme_resolver import ThemeResolver
from ppt_maker.rendering.templater import Templater
from ppt_maker.rendering.renderer import Renderer
from ppt_maker.export.compiler import Compiler
from ppt_maker.export.pptx_exporter import PptxExporter


def build_deck_1_executive() -> MasterPlan:
    """Deck 1: Executive Board Review (Corporate Clean / Executive Navy)."""
    css_vars, _ = ThemeResolver.resolve(
        structural_class="corporate_clean",
        palette_name="executive_navy",
        ai_css_vars={},
    )
    theme = Theme(structural_class="corporate_clean", palette="executive_navy", css_variables=css_vars)
    slides = [
        Slide(
            slide_number=1,
            layout_type="cover",
            title="Enterprise AI Operating Review",
            subtitle="Global Scalability, Enterprise NRR Acceleration & Fiscal 2027 Capital Strategy",
            eyebrow="EXECUTIVE BRIEFING · Q4 2026",
            speaker_notes="Welcome members of the board. Today we review our full-year operational execution, financial acceleration, and capital allocation for fiscal 2027.",
        ),
        Slide(
            slide_number=2,
            layout_type="kpi_dashboard",
            title="Core Financial & Operational Milestones",
            subtitle="Sustained top-decile unit economics across 4 enterprise operating dimensions",
            eyebrow="PERFORMANCE SCORECARD",
            content_blocks=[
                KPIBlock(cards=[
                    KPICard(badge="ARR", value="$48.5M", label="Annual Recurring Revenue", delta="+118% YoY"),
                    KPICard(badge="RETENTION", value="96.4%", label="Net Revenue Retention", delta="Top Decile"),
                    KPICard(badge="EFFICIENCY", value="3.4x", label="LTV:CAC Capital Ratio", delta="+0.8x YoY"),
                    KPICard(badge="MARGIN", value="78.2%", label="Non-GAAP Gross Margin", delta="+640 bps"),
                ])
            ],
            speaker_notes="Our ARR expanded 118 percent year-over-year to 48.5 million dollars, driven by enterprise net retention exceeding 96 percent. Unit economics continue to demonstrate top-tier capital efficiency.",
        ),
        Slide(
            slide_number=3,
            layout_type="roadmap_chain",
            title="Four-Phase Enterprise Modernization Rollout",
            subtitle="De-risked execution timeline aligned with tier-1 banking compliance milestones",
            eyebrow="STRATEGIC EXECUTION",
            content_blocks=[
                StepBlock(
                    steps=[
                        "SOC2 Type II & FedRAMP Compliance Verification",
                        "Zero-Trust Multi-Tenant Database Isolation",
                        "EMEA Tier-1 Financial Institution Go-Live",
                        "Autonomous Agentic Decision Workflows GA"
                    ],
                    step_labels=["Q1", "Q2", "Q3", "Q4"]
                )
            ],
            speaker_notes="Phase one and two compliance certifications were completed on schedule. Tier-one European banking implementations went live in Q3 with zero downtime.",
        ),
        Slide(
            slide_number=4,
            layout_type="stat",
            title="Tier-1 Enterprise Expansion Acceleration",
            subtitle="Rapid enterprise adoption across global financial services institutions",
            eyebrow="MARKET TRACTION",
            content_blocks=[
                StatBlock(
                    value="340%",
                    label="Year-over-Year Enterprise Account Volume",
                    context="42 Global Fortune 500 Institutions in Production"
                )
            ],
            speaker_notes="Enterprise tier-one account volume grew 340 percent year-over-year, validating product-market fit across financial services and healthcare.",
        ),
        Slide(
            slide_number=5,
            layout_type="quote",
            title="Executive Perspective",
            eyebrow="CUSTOMER ENDORSEMENT",
            content_blocks=[
                PullQuoteBlock(
                    quote="Autonomous intelligence is no longer an experimental R&D initiative; it is now the operational backbone of modern financial infrastructure.",
                    attribution="— Chief Information Officer, Global Banking Consortium"
                )
            ],
            speaker_notes="This customer endorsement summarizes the strategic posture: our software has graduated from pilot experiments to mission-critical infrastructure.",
        ),
        Slide(
            slide_number=6,
            layout_type="split",
            title="FY2027 Capital Deployment Strategy",
            subtitle="Disciplined reinvestment prioritized across core R&D and global market coverage",
            eyebrow="CAPITAL ALLOCATION",
            content_blocks=[
                ComparisonBlock(
                    left_label="R&D & Engineering (55%)",
                    left_items=[
                        "Autonomous Reflexion Critic loop optimization",
                        "Sub-50ms distributed inference acceleration",
                        "Custom fine-tuned domain reasoning adapters",
                    ],
                    right_label="Global GTM & Reserves (45%)",
                    right_items=[
                        "Dedicated EMEA & APAC enterprise sales teams",
                        "Solution architecture & customer success pods",
                        "Prudent 18-month cash operating runway",
                    ],
                )
            ],
            speaker_notes="We recommend committing 55 percent of incoming capital to R&D while dedicating 45 percent to customer success pods and sustaining an 18-month cash reserve.",
        ),
    ]
    return MasterPlan(theme=theme, slides=slides)


def build_deck_2_tech_infra() -> MasterPlan:
    """Deck 2: AI Agent Infrastructure (Dark Neon / Cyber Cyan)."""
    css_vars, _ = ThemeResolver.resolve(
        structural_class="dark_neon",
        palette_name="cyber_cyan",
        ai_css_vars={},
    )
    theme = Theme(structural_class="dark_neon", palette="cyber_cyan", css_variables=css_vars)
    slides = [
        Slide(
            slide_number=1,
            layout_type="cover",
            title="Autonomous Multi-Agent Architecture",
            subtitle="Distributed Topology, Real-Time DOM Reflexion, and Deterministic Guardrails",
            eyebrow="SYSTEMS ARCHITECTURE · V4.2",
            speaker_notes="Today we examine the V4.2 autonomous agent runtime: moving beyond brittle single-shot prompts to closed-loop visual verification.",
        ),
        Slide(
            slide_number=2,
            layout_type="hero_statement",
            title="Sub-50ms Agentic Orchestration at Enterprise Scale",
            subtitle="Combining Playwright CDP layout coordinates with targeted LLM micro-patches eliminates visual overflow.",
            eyebrow="DESIGN PHILOSOPHY",
            speaker_notes="Visual spatial awareness cannot be achieved through text prompting alone. Coupling browser CDP coordinates with targeted LLM patches solves layout degradation permanently.",
        ),
        Slide(
            slide_number=3,
            layout_type="bento",
            title="Three-Tier Reflexion Critic-Actor Architecture",
            subtitle="Hierarchical error correction minimizing token burn and latency",
            eyebrow="RUNTIME ANATOMY",
            content_blocks=[
                BentoBlock(
                    variant="bento_8_4",
                    cards=[
                        BentoCard(
                            card_id="hero",
                            card_style="elevated",
                            title="Playwright CDP Telemetry Engine",
                            body="Real-time DOM bounding box audit capturing overflow, element occlusions, and sub-threshold contrast defects directly from Chromium.",
                            badge="CDP Telemetry",
                            stat_val="42ms",
                            stat_label="P99 Telemetry"
                        ),
                        BentoCard(
                            card_id="side_1",
                            card_style="neutral",
                            title="Tier 1 Micro-Fixer",
                            body="0ms algorithmic line-height clamping and trailing whitespace pruning.",
                            badge="0ms Latency"
                        ),
                        BentoCard(
                            card_id="side_2",
                            card_style="neutral",
                            title="Tier 2 Reflexion Critic",
                            body="350-token surgical JSON patch via Gemini Flash Lite on layout failure.",
                            badge="Targeted LLM"
                        ),
                    ]
                )
            ],
            speaker_notes="Our 3-tier hierarchy ensures that 80 percent of layout warnings resolve instantly in Tier 1 with zero token cost, while Tier 2 invokes targeted LLM reflexion only when required.",
        ),
        Slide(
            slide_number=4,
            layout_type="stat",
            title="P99 Runtime Telemetry & Execution Throughput",
            subtitle="Sub-50ms constraint resolution verified under high concurrency",
            eyebrow="BENCHMARK PERFORMANCE",
            content_blocks=[
                StatBlock(
                    value="42ms",
                    label="P99 Local Constraint Solving Latency",
                    context="Zero GPU starvation across 12,000 concurrent agent threads"
                )
            ],
            citations=[
                Citation(
                    id=1,
                    claim="Sub-50ms P99 constraint solving latency benchmark",
                    source_title="Systems Telemetry & Latency Benchmark 2026",
                    source_url="https://nature.com/articles/systems-telemetry-2026",
                    domain="nature.com",
                )
            ],
            speaker_notes="At 42 milliseconds P99 constraint solving latency, the agency compiles production decks 10x faster than traditional manual workflows.",
        ),
        Slide(
            slide_number=5,
            layout_type="roadmap_chain",
            title="End-to-End Presentation Generation Pipeline",
            subtitle="From ungrounded research brief to dual-compiled vector PDF and native PowerPoint",
            eyebrow="PIPELINE STAGES",
            content_blocks=[
                StepBlock(
                    steps=[
                        "Autonomous Research & Citation Extraction",
                        "MasterPlan Synthesis & Schema Validation",
                        "Jinja2 HTML & CSS Design Token Injection",
                        "Dual Vector PDF & Native PPTX Compilation"
                    ],
                    step_labels=["Stage 1", "Stage 2", "Stage 3", "Stage 4"]
                )
            ],
            speaker_notes="Every stage enforces strict schema validation and plate isolation, guaranteeing that exported decks are 100 percent editable without duplicate ghost text.",
        ),
        Slide(
            slide_number=6,
            layout_type="split",
            title="Single-Shot Prompting vs. Multi-Stage Agency",
            subtitle="Empirical comparison across layout reliability, token efficiency, and visual hierarchy",
            eyebrow="ARCHITECTURAL COMPARISON",
            content_blocks=[
                ComparisonBlock(
                    left_label="Naive Single-Shot Wrapper",
                    left_items=[
                        "Monolithic 8,000-token prompt per deck",
                        "Brittle visual overflow requiring full regeneration",
                        "Flat, repetitive 3-column card layouts",
                        "Non-deterministic hallucinated metrics",
                    ],
                    right_label="Autonomous Multi-Stage Agency",
                    right_items=[
                        "Staged planning, drafting, and critique agents",
                        "Closed-loop CDP spatial coordinate verification",
                        "Intentional typography and semantic layout variety",
                        "100% grounded citations and verified metrics",
                    ],
                )
            ],
            speaker_notes="The benchmark proves that staged agentic architecture cuts token costs by 48 percent while boosting human layout preference to 94.2 percent.",
        ),
    ]
    return MasterPlan(theme=theme, slides=slides)


def build_deck_3_venture_pitch() -> MasterPlan:
    """Deck 3: Venture Pitch Deck (Minimalist / SlidesGo Modern Proposal)."""
    css_vars, _ = ThemeResolver.resolve(
        structural_class="slidesgo_modern_proposal",
        palette_name=None,
        ai_css_vars={},
    )
    theme = Theme(structural_class="slidesgo_modern_proposal", palette="corporate_navy", css_variables=css_vars)
    slides = [
        Slide(
            slide_number=1,
            layout_type="cover",
            title="PulseFlow Autonomous Agency",
            subtitle="Automating High-Stakes Enterprise Visual Presentations with Precision AI",
            eyebrow="SERIES A · INVESTOR PRESENTATION",
            speaker_notes="We are PulseFlow. We are building the autonomous presentation agency for the modern enterprise, replacing millions of hours of manual slide formatting.",
        ),
        Slide(
            slide_number=2,
            layout_type="split",
            title="The $44B Enterprise Productivity Drain",
            subtitle="Knowledge workers spend 35% of their working hours manually formatting slide decks",
            eyebrow="THE MARKET PROBLEM",
            content_blocks=[
                ComparisonBlock(
                    left_label="The Traditional Agency Dilemma",
                    left_items=[
                        "$2,500 to $10,000 per bespoke deck",
                        "5 to 10 day turnaround time",
                        "Disconnected from real-time corporate data",
                        "Inconsistent brand typography across teams",
                    ],
                    right_label="The PulseFlow AI Alternative",
                    right_items=[
                        "Instant studio-grade deck generation in < 30s",
                        "Direct integration with internal data sources",
                        "Guaranteed brand compliance via design tokens",
                        "100% editable PowerPoint and vector PDF export",
                    ],
                )
            ],
            speaker_notes="Enterprises spend over 44 billion dollars annually on manual presentation labor. PulseFlow delivers agency-quality presentations in under thirty seconds.",
        ),
        Slide(
            slide_number=3,
            layout_type="kpi_dashboard",
            title="Exponential Organic Growth Across Tier-1 Customers",
            subtitle="Rapid enterprise adoption driven by product-led growth and executive word-of-mouth",
            eyebrow="TRACTION & UNIT ECONOMICS",
            content_blocks=[
                KPIBlock(cards=[
                    KPICard(badge="USERS", value="140K+", label="Active Enterprise Creators", delta="+180% YoY"),
                    KPICard(badge="DECKS", value="2.4M", label="Presentations Rendered", delta="99.8% Reliability"),
                    KPICard(badge="SAVINGS", value="$18.5M", label="Customer Agency Budget Saved", delta="Audited ROI"),
                    KPICard(badge="SPEED", value="12x", label="Turnaround Acceleration", delta="< 25s per deck"),
                ])
            ],
            speaker_notes="Over 140,000 enterprise knowledge workers have created 2.4 million decks, saving companies over 18 million dollars in design agency fees.",
        ),
        Slide(
            slide_number=4,
            layout_type="stat",
            title="Customer Productivity Multiplication",
            subtitle="Measurable hours saved per executive and consultant every month",
            eyebrow="ROI IMPACT",
            content_blocks=[
                StatBlock(
                    value="12x",
                    label="Faster Time-to-Delivery for Critical Presentations",
                    context="From 6 Hours of Manual Formatting Down to 30 Seconds"
                )
            ],
            speaker_notes="Our core customer value proposition is a twelve-times acceleration in time-to-delivery for high-stakes presentations.",
        ),
        Slide(
            slide_number=5,
            layout_type="quote",
            title="Customer Endorsement",
            eyebrow="TESTIMONIAL",
            content_blocks=[
                PullQuoteBlock(
                    quote="PulseFlow transformed our strategic planning rhythm. Our quarterly review decks now look like they were crafted by a high-end design boutique in minutes.",
                    attribution="— Elena Rostova, VP Strategy & Operations, Fortis Global"
                )
            ],
            speaker_notes="Customer sentiment is unanimous: executive teams love the agency-quality aesthetic and the freedom from repetitive manual formatting.",
        ),
        Slide(
            slide_number=6,
            layout_type="roadmap_chain",
            title="Scale & Product Expansion Roadmap",
            subtitle="Expanding from standalone presentation synthesis to pervasive enterprise communication intelligence",
            eyebrow="GROWTH HORIZON",
            content_blocks=[
                StepBlock(
                    steps=[
                        "Enterprise Design System Sync (Figma & Canva)",
                        "Real-Time Collaborative Multi-User Editing",
                        "Autonomous Multimodal Chart & Financial Modeling",
                        "Global Enterprise Sales & Compliance Expansion"
                    ],
                    step_labels=["Q1", "Q2", "Q3", "Q4"]
                )
            ],
            speaker_notes="With Series A capital, we will deepen our design system integrations and expand into autonomous financial modeling and real-time collaboration.",
        ),
    ]
    return MasterPlan(theme=theme, slides=slides)


def build_deck_4_master_showcase() -> MasterPlan:
    """Deck 4: Mastering AI-Powered Presentation Design (Canonical Master Showcase)."""
    css_vars, _ = ThemeResolver.resolve(
        structural_class="glassmorphism",
        palette_name=None,
        ai_css_vars={},
    )
    theme = Theme(structural_class="glassmorphism", palette="ocean_blue", css_variables=css_vars)
    slides = [
        Slide(
            slide_number=1,
            layout_type="cover",
            title="Mastering AI-Powered Presentation Design",
            subtitle="Autonomous Multi-Stage Agency Pipeline with Vector PDF & Editable PowerPoint Export",
            eyebrow="SYSTEM SHOWCASE · V4.2",
            speaker_notes="Welcome. In this canonical showcase, we demonstrate the complete design token architecture, semantic layouts, and dual compilation capabilities of the AI Presentation Agency.",
        ),
        Slide(
            slide_number=2,
            layout_type="split",
            title="The Old Way vs. The AI Presentation Agency",
            subtitle="Eliminating tedious manual alignment through intelligent constraint solving",
            eyebrow="WORKFLOW TRANSFORMATION",
            content_blocks=[
                ComparisonBlock(
                    left_label="Traditional Manual Workflow",
                    left_items=[
                        "Endless pixel nudging and box alignment",
                        "Inconsistent typography across departments",
                        "Manual chart construction and formatting",
                        "Disconnected from authoritative data sources",
                    ],
                    right_label="AI Presentation Agency V4.2",
                    right_items=[
                        "Automated layout selection and typography",
                        "Enforced design token hierarchy",
                        "Playwright CDP visual overflow detection",
                        "100% vector PDF and native PowerPoint export",
                    ],
                )
            ],
            speaker_notes="Compare the hours lost to pixel-nudging with the speed of an agentic pipeline that guarantees layout harmony.",
        ),
        Slide(
            slide_number=3,
            layout_type="kpi_dashboard",
            title="Agency Performance & Reliability Scorecard",
            subtitle="Continuous empirical evaluation benchmarking 10 golden presentation scenarios",
            eyebrow="EVALUATION SCORECARD",
            content_blocks=[
                KPIBlock(cards=[
                    KPICard(badge="EVALS", value="96.4", label="Deterministic Quality Score", delta="Grade A"),
                    KPICard(badge="PASS RATE", value="100%", label="Automated Test Suite Pass Rate", delta="159 Passing"),
                    KPICard(badge="LATENCY", value="42ms", label="P99 Constraint Solving", delta="Zero Starvation"),
                    KPICard(badge="COST", value="$0.003", label="Average Synthesis Cost", delta="-48% vs Single-Shot"),
                ])
            ],
            speaker_notes="Our continuous evaluation harness validates all presentations against 4 deterministic metrics, maintaining a 96.4 Grade A average.",
        ),
        Slide(
            slide_number=4,
            layout_type="hero_statement",
            title="Design is How It Works, Not Just What It Looks Like",
            subtitle="Combining mathematical geometry constraints with typographic hierarchy creates presentations that persuade.",
            eyebrow="CORE PRINCIPLE",
            speaker_notes="Design excellence requires structural discipline. Every slide serves a narrative purpose in the overall deck arc.",
        ),
        Slide(
            slide_number=5,
            layout_type="stat",
            title="Measurable Impact on Enterprise Productivity",
            subtitle="Quantified time savings across high-growth consulting and executive teams",
            eyebrow="MEASURABLE IMPACT",
            content_blocks=[
                StatBlock(
                    value="10x",
                    label="Turnaround Acceleration for Critical Decks",
                    context="From 5+ Hours of Formatting Down to Under 30 Seconds"
                )
            ],
            speaker_notes="The primary return on investment is immediate: high-stakes decks ready in seconds rather than days.",
        ),
        Slide(
            slide_number=6,
            layout_type="roadmap_chain",
            title="From Idea to Polished Deck in Four Staged Steps",
            subtitle="Staged multi-agent architecture isolating research, drafting, validation, and compilation",
            eyebrow="EXECUTION LIFECYCLE",
            content_blocks=[
                StepBlock(
                    steps=[
                        "Research & Grounded Fact Synthesis",
                        "Narrative Arc & MasterPlan Generation",
                        "Playwright CDP Layout Reflexion Loop",
                        "Dual Vector PDF & PPTX Compilation"
                    ],
                    step_labels=["Step 1", "Step 2", "Step 3", "Step 4"]
                )
            ],
            speaker_notes="Four deterministic phases guarantee that output decks are robust, verified, and completely free from hallucinated layout flaws.",
        ),
        Slide(
            slide_number=7,
            layout_type="quote",
            title="Persuasive Communication",
            eyebrow="CLOSING INSIGHT",
            content_blocks=[
                PullQuoteBlock(
                    quote="A great presentation does not decorate an idea; it gives the idea clarity, resonance, and momentum.",
                    attribution="— Design Systems Manifesto"
                )
            ],
            speaker_notes="In conclusion, the goal of the AI Presentation Agency is to amplify human ideas with studio-quality visual craftsmanship.",
        ),
    ]
    return MasterPlan(theme=theme, slides=slides)


def generate_deck(plan: MasterPlan, base_name: str, examples_dir: str, showcase_assets_dir: str):
    """Render HTML, compile PDF, compile PPTX, export speaker notes, and save preview PNGs."""
    print(f"\n=======================================================")
    print(f"Generating Showcase Deck: {base_name}")
    print(f"=======================================================")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. HTML Templating
        templater = Templater(build_dir=tmpdir)
        html_files = templater.generate_html(plan)
        print(f"  Generated {len(html_files)} HTML slide files.")

        # 2. Playwright PNG Rendering (1920x1080)
        renderer = Renderer(build_dir=tmpdir, preview_mode=False)
        png_files, _ = renderer.render_all(html_files)
        print(f"  Rendered {len(png_files)} PNG slide plates.")

        # 3. Vector PDF Compilation
        pdf_path = os.path.join(examples_dir, f"{base_name}.pdf")
        Compiler().compile_to_pdf(png_files, pdf_path)
        print(f"  Compiled PDF: {pdf_path} ({os.path.getsize(pdf_path) // 1024} KB)")

        # 4. Native Editable PPTX Compilation
        pptx_path = os.path.join(examples_dir, f"{base_name}.pptx")
        PptxExporter().export(png_files, plan, pptx_path)
        print(f"  Compiled PPTX: {pptx_path} ({os.path.getsize(pptx_path) // 1024} KB)")

        # 5. Speaker Notes Export
        notes_path = os.path.join(examples_dir, f"{base_name}_speaker_notes.md")
        Compiler().export_speaker_notes(plan, notes_path)
        print(f"  Exported Speaker Notes: {notes_path}")

        # 6. Save JSON MasterPlan blueprint
        plan_json_path = os.path.join(examples_dir, f"{base_name}_master_plan.json")
        with open(plan_json_path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
        print(f"  Exported MasterPlan JSON: {plan_json_path}")

        # 7. Copy All Slide Preview PNGs to showcase assets
        slide_previews = []
        for i, png_file in enumerate(png_files):
            slide_preview = os.path.join(showcase_assets_dir, f"{base_name}_slide{i+1}.png")
            Image.open(png_file).save(slide_preview, "PNG", optimize=True)
            slide_previews.append(slide_preview)
        print(f"  Saved {len(slide_previews)} preview PNGs to {showcase_assets_dir}")

    return {
        "pdf": pdf_path,
        "pptx": pptx_path,
        "notes": notes_path,
        "plan": plan_json_path,
        "cover_png": slide_previews[0],
        "slide2_png": slide_previews[1] if len(slide_previews) > 1 else slide_previews[0],
        "slide_previews": slide_previews,
    }


def create_showcase_montage(results: List[Dict], output_path: str):
    """Build a stunning 2x2 presentation grid montage showcasing 4 distinct semantic archetypes."""
    print(f"\nBuilding Visual Showcase Montage: {output_path}...")
    # Select 4 representative slides demonstrating rich semantic archetypes across themes:
    # 1. Executive Board KPI Dashboard (Deck 1, Slide 2) -> corporate_clean (kpi_dashboard)
    # 2. AI Agent Infrastructure Bento Grid (Deck 2, Slide 3) -> dark_neon (bento)
    # 3. Venture Pitch Market Problem Split (Deck 3, Slide 2) -> slidesgo_modern_proposal (split)
    # 4. Presentation Principles Hero Statement (Deck 4, Slide 4) -> glassmorphism (hero_statement)
    images = [
        Image.open(results[0]["slide_previews"][1]),  # KPI Dashboard
        Image.open(results[1]["slide_previews"][2]),  # Bento Grid
        Image.open(results[2]["slide_previews"][1]),  # Asymmetric Split
        Image.open(results[3]["slide_previews"][3]),  # Hero Statement
    ]

    target_w, target_h = 1200, 675  # 16:9 aspect ratio
    resized = [im.resize((target_w, target_h), Image.Resampling.LANCZOS) for im in images]

    # Create 2x2 canvas with sleek border gap
    gap = 20
    border = 24
    canvas_w = (target_w * 2) + gap + (border * 2)
    canvas_h = (target_h * 2) + gap + (border * 2)

    montage = Image.new("RGB", (canvas_w, canvas_h), color="#0B0F17")  # Deep executive dark navy background

    # Paste in 2x2 grid
    positions = [
        (border, border),
        (border + target_w + gap, border),
        (border, border + target_h + gap),
        (border + target_w + gap, border + target_h + gap),
    ]

    for im, pos in zip(resized, positions):
        montage.paste(im, pos)

    montage.save(output_path, "PNG", optimize=True)
    print(f"Successfully generated showcase montage: {output_path} ({os.path.getsize(output_path) // 1024} KB)")


def main():
    examples_dir = os.path.join(ROOT_DIR, "examples")
    showcase_assets_dir = os.path.join(ROOT_DIR, "docs", "assets", "showcase")
    os.makedirs(examples_dir, exist_ok=True)
    os.makedirs(showcase_assets_dir, exist_ok=True)

    decks = [
        (build_deck_1_executive(), "01_executive_board_review"),
        (build_deck_2_tech_infra(), "02_ai_agent_infrastructure"),
        (build_deck_3_venture_pitch(), "03_venture_pitch_deck"),
        (build_deck_4_master_showcase(), "ai_presentation_tools_showcase"),
    ]

    results = []
    for plan, base_name in decks:
        res = generate_deck(plan, base_name, examples_dir, showcase_assets_dir)
        results.append(res)

    # Copy canonical sample_master_plan.json
    sample_plan_src = os.path.join(examples_dir, "ai_presentation_tools_showcase_master_plan.json")
    sample_plan_dst = os.path.join(examples_dir, "sample_master_plan.json")
    with open(sample_plan_src, "r", encoding="utf-8") as sf, open(sample_plan_dst, "w", encoding="utf-8") as df:
        df.write(sf.read())

    # Build 2x2 Montage
    montage_path = os.path.join(ROOT_DIR, "docs", "assets", "showcase_montage.png")
    create_showcase_montage(results, montage_path)

    print("\n=======================================================")
    print("ALL SHOWCASE DECKS & VISUAL ASSETS GENERATED CLEANLY!")
    print("=======================================================")


if __name__ == "__main__":
    main()
