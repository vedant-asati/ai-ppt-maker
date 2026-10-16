import argparse
import sys
import os
import time
from dotenv import load_dotenv
load_dotenv()

try:
    from ppt_maker.core.config_manager import ConfigManager
except ImportError:
    from config_manager import ConfigManager


def pre_flight_validation(config):
    """Pre-flight validation — fails fast before spending tokens."""
    api_key = os.environ.get("GEMINI_API_KEY")

    # Unified access for both AppConfig and raw dict
    source_text = (ConfigManager.get(config, 'source_text') or '').strip()
    source_file = (ConfigManager.get(config, 'source_file') or '').strip()

    has_source = bool(source_text) or bool(source_file)
    if not has_source:
        print("Error: You must provide either 'source_text' or 'source_file' in the config.")
        sys.exit(1)

    if source_file and not os.path.exists(source_file):
        print(f"Error: The source_file '{source_file}' does not exist.")
        sys.exit(1)

    if not api_key:
        if not source_file and len(source_text) < 200:
            print("Error: You provided a short prompt but no GEMINI_API_KEY is set.")
            print("  → A short prompt requires the AI Planner. Set GEMINI_API_KEY in .env")
            print("  → Or run with: --offline-plan master_plan.json")
            sys.exit(1)

    return True


def _resolve_output_paths(config):
    """Returns (pdf_path, notes_path, export_notes)."""
    # Handle both AppConfig and raw dict
    try:
        from ppt_maker.core.config_manager import _PYDANTIC_AVAILABLE, AppConfig
    except ImportError:
        from config_manager import _PYDANTIC_AVAILABLE, AppConfig
    if _PYDANTIC_AVAILABLE and isinstance(config, AppConfig):
        output_dir = (config.output.output_dir or '.').rstrip('/')
        pdf_name   = config.output.pdf_filename or 'presentation.pdf'
        notes_name = config.output.speaker_notes_filename or pdf_name.replace('.pdf', '_speaker_notes.md')
        export_notes = config.output.export_speaker_notes
    else:
        output_cfg   = (config.get('output') or {})
        output_dir   = (output_cfg.get('output_dir') or '.').rstrip('/')
        pdf_name     = output_cfg.get('pdf_filename') or 'presentation.pdf'
        notes_name   = output_cfg.get('speaker_notes_filename') or pdf_name.replace('.pdf', '_speaker_notes.md')
        export_notes = output_cfg.get('export_speaker_notes', True)

    if output_dir and output_dir != '.':
        os.makedirs(output_dir, exist_ok=True)

    pdf_path   = os.path.join(output_dir, pdf_name)   if output_dir != '.' else pdf_name
    notes_path = os.path.join(output_dir, notes_name) if output_dir != '.' else notes_name
    return pdf_path, notes_path, export_notes


def _get_design_prefs(config):
    """Extract design preferences from either AppConfig or raw dict."""
    try:
        from ppt_maker.core.config_manager import _PYDANTIC_AVAILABLE, AppConfig
    except ImportError:
        from config_manager import _PYDANTIC_AVAILABLE, AppConfig
    if _PYDANTIC_AVAILABLE and isinstance(config, AppConfig):
        return {
            'theme_style':   config.design_preferences.theme_style,
            'palette':       config.design_preferences.palette,
            'primary_color': config.design_preferences.primary_color,
        }
    design = config.get('design_preferences') or {}
    return {
        'theme_style':   design.get('theme_style', 'corporate_clean'),
        'palette':       design.get('palette'),
        'primary_color': design.get('primary_color'),
    }


def main():
    parser = argparse.ArgumentParser(
        description="AI Presentation Agency — generate beautiful PDF presentations from a config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Quick start:\n"
            "  python cli.py init        # create config.yaml\n"
            "  python cli.py generate    # build presentation.pdf\n"
            "  python cli.py audit       # run design quality audit\n"
            "  python cli.py fonts       # download fonts for offline rendering"
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── init ──────────────────────────────────────────────────────────────
    init_parser = subparsers.add_parser("init", help="Generate a default config.yaml")
    init_parser.add_argument("--config", default="config.yaml")

    # ── generate ──────────────────────────────────────────────────────────
    gen_parser = subparsers.add_parser("generate", help="Generate the presentation")
    gen_parser.add_argument("--config", default="config.yaml")
    gen_parser.add_argument("--dry-run", action="store_true",
                            help="Stop after AI planning. Saves master_plan.json for review.")
    gen_parser.add_argument("--offline-plan", metavar="PLAN_JSON",
                            help="Skip AI planning. Render a pre-existing master_plan.json.")
    gen_parser.add_argument("--force-images", action="store_true",
                            help="Re-generate all images even if cached.")
    gen_parser.add_argument("--clean-images", action="store_true",
                            help="Remove all cached images before generating.")
    gen_parser.add_argument("--preview", action="store_true",
                            help="Render first 3 slides at 960x540 for fast preview.")
    gen_parser.add_argument("--audit", choices=["quick", "full", "ai"], default=None,
                            help="Run design audit after generation.")
    gen_parser.add_argument("--score", action="store_true",
                            help="Print per-slide content quality scores after planning.")
    gen_parser.add_argument("--pptx", action="store_true",
                            help="Also export an editable .pptx file alongside PDF.")
    gen_parser.add_argument("--slides", type=int, default=None, metavar="N",
                            help="Number of slides (3-20). Overrides config slide_count.")
    gen_parser.add_argument("--images-dir", default=None, metavar="DIR",
                            help="Directory of user photos to match to slides.")

    # ── audit ─────────────────────────────────────────────────────────────
    audit_parser = subparsers.add_parser("audit", help="Run design audit on generated slides")
    audit_parser.add_argument("--level", choices=["quick", "full", "ai"], default="full")
    audit_parser.add_argument("--slides-dir", default="temp_build/images/")
    audit_parser.add_argument("--plan", default="master_plan.json")
    audit_parser.add_argument("--out", default="design_audit.md")
    audit_parser.add_argument("--config", default="config.yaml")
    audit_parser.add_argument("--score", action="store_true",
                              help="Include per-slide content scores in the audit report.")

    # ── fonts ────────────────────────────────────────────────────────
    fonts_parser = subparsers.add_parser(
        "fonts",
        help="Download Google Fonts for fully offline rendering (no network during PDF generation)"
    )
    fonts_parser.add_argument(
        "--dir", default="assets/fonts",
        help="Directory to save font files (default: assets/fonts)"
    )
    fonts_parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-file progress output"
    )

    args = parser.parse_args()

    # ══════════════════════════════════════════════════════════════════════
    # fonts
    # ══════════════════════════════════════════════════════
    if args.command == "fonts":
        print("Downloading Google Fonts for offline rendering...")
        try:
            try:
                from ppt_maker.design.font_downloader import download_fonts
            except ImportError:
                from font_downloader import download_fonts
            ok = download_fonts(fonts_dir=args.dir, verbose=not args.quiet)
            if ok:
                print("\n  All fonts are ready. Future renders will use local fonts (faster + offline).")
            else:
                print("\n  Some fonts failed to download. Check your internet connection and retry.")
                sys.exit(1)
        except ImportError:
            print("Error: font_downloader.py not found.")
            sys.exit(1)
        return

    # ══════════════════════════════════════════════════════════════════════
    # init
    # ══════════════════════════════════════════════════════════════════════
    if args.command == "init":
        ConfigManager.init_config(args.config)
        return

    # ══════════════════════════════════════════════════════════════════════
    # audit (standalone — acts on already-generated slides)
    # ══════════════════════════════════════════════════════════════════════
    elif args.command == "audit":
        if not os.path.exists(args.slides_dir):
            print(f"Error: Slides directory '{args.slides_dir}' not found.")
            print("  → Run `python cli.py generate` first.")
            sys.exit(1)
        if not os.path.exists(args.plan):
            print(f"Error: Master plan '{args.plan}' not found.")
            print("  → Run `python cli.py generate --dry-run` to create one.")
            sys.exit(1)
        dom_cache = os.path.join('temp_build', 'dom_audit.json')
        if not os.path.exists(dom_cache):
            print("  [Info] No cached DOM audit data — Layer 1 (DOM checks) will be skipped.")
        if args.level == 'ai' and not os.environ.get('GEMINI_API_KEY'):
            print("  [Warning] GEMINI_API_KEY not set — downgrading to level 'full'.")
            args.level = 'full'

        import json
        try:
            from ppt_maker.core.schemas import MasterPlan
        except ImportError:
            from schemas import MasterPlan
        config = ConfigManager.load_and_validate(args.config)
        with open(args.plan, 'r', encoding='utf-8') as f:
            mp = MasterPlan(**json.load(f))

        try:
            try:
                from ppt_maker.audit.quality_checker import QualityChecker
            except ImportError:
                from quality_checker import QualityChecker
            checker = QualityChecker()
            checker.run_audit(
                slides_dir=args.slides_dir,
                master_plan=mp,
                config=config,
                level=args.level,
                dom_cache_path=dom_cache if os.path.exists(dom_cache) else None,
                output_path=args.out,
            )
        except ImportError:
            print("Error: quality_checker.py not found. Implement Phase 4C first.")
            sys.exit(1)

        # Optional per-slide content scoring
        if getattr(args, 'score', False):
            try:
                try:
                    from ppt_maker.planning.content_scorer import score_and_print
                except ImportError:
                    from content_scorer import score_and_print
                score_and_print(mp, verbose=True)
            except ImportError:
                pass
        return

    # ══════════════════════════════════════════════════════════════════════
    # generate
    # ══════════════════════════════════════════════════════════════════════
    elif args.command == "generate":
        run_start = time.time()

        print(f"Loading config from {args.config}...")
        config = ConfigManager.load_and_validate(args.config)

        # CLI overrides
        if getattr(args, 'slides', None):
            n = max(3, min(20, args.slides))
            # config may be Pydantic model or raw dict
            goals = getattr(config, 'presentation_goals', None)
            if goals is not None and hasattr(goals, 'slide_count'):
                goals.slide_count = n
            elif isinstance(config, dict):
                config.setdefault('presentation_goals', {})['slide_count'] = n
            print(f"  [Override] --slides {n}")

        if args.offline_plan:
            if not os.path.exists(args.offline_plan):
                print(f"Error: --offline-plan file '{args.offline_plan}' not found.")
                sys.exit(1)
        else:
            print("Running pre-flight validation...")
            pre_flight_validation(config)
            print("Pre-flight validation passed. Starting pipeline...")

        pdf_path, notes_path, export_notes = _resolve_output_paths(config)
        design = _get_design_prefs(config)

        # Print run summary
        goals_obj = ConfigManager.get(config, 'presentation_goals') or {}
        if hasattr(goals_obj, 'audience'):
            audience = goals_obj.audience
            duration = goals_obj.duration_minutes
        else:
            audience = (goals_obj or {}).get('audience', 'General')
            duration = (goals_obj or {}).get('duration_minutes', '?')

        print(f"\n  Target:   {audience} | {duration} min | {design['theme_style']} theme")
        print(f"  Output:   {pdf_path}\n")

        # ── Phase 1: Planning ─────────────────────────────────────────────
        if args.offline_plan:
            import json
            try:
                from ppt_maker.core.schemas import MasterPlan
            except ImportError:
                from schemas import MasterPlan
            print(f"Offline Mode: Loading master plan from {args.offline_plan}")
            with open(args.offline_plan, 'r', encoding='utf-8') as f:
                master_plan = MasterPlan(**json.load(f))
        else:
            try:
                from ppt_maker.planning.planner import Planner
            except ImportError:
                from planner import Planner
            planner = Planner()
            master_plan = planner.generate_master_plan(config)

        # ── Phase 2: Validation ───────────────────────────────────────────
        try:
            from ppt_maker.planning.validator import ContentValidator
        except ImportError:
            from validator import ContentValidator
        master_plan = ContentValidator.validate_and_prune(master_plan)

        # ── Optional: Content quality scoring ────────────────────────────
        if getattr(args, 'score', False):
            try:
                try:
                    from ppt_maker.planning.content_scorer import score_and_print
                except ImportError:
                    from content_scorer import score_and_print
                score_and_print(master_plan, verbose=True)
            except ImportError:
                pass

        # ── Phase 2.5: Theme Resolution ───────────────────────────────────
        try:
            from ppt_maker.design.theme_resolver import ThemeResolver
        except ImportError:
            from theme_resolver import ThemeResolver
        resolved_vars, resolved_palette = ThemeResolver.resolve(
            structural_class=master_plan.theme.structural_class,
            palette_name=master_plan.theme.palette or design.get('palette'),
            ai_css_vars=master_plan.theme.css_variables,
            user_color=design.get('primary_color'),
        )
        master_plan.theme.css_variables = resolved_vars
        master_plan.theme.palette = resolved_palette

        # ── Dry-run exit ──────────────────────────────────────────────────
        if args.dry_run:
            out_file = "master_plan.json"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(master_plan.model_dump_json(indent=2))
            elapsed = time.time() - run_start
            print(f"\n--dry-run complete in {elapsed:.1f}s. Blueprint saved to {out_file}")
            print(f"  Theme: {master_plan.theme.structural_class} / {resolved_palette or 'AI-colored'}")
            print(f"  Edit freely, then render with: python cli.py generate --offline-plan {out_file}")
            sys.exit(0)

        # ── Clean stale build artifacts ───────────────────────────────────
        import shutil
        build_images_dir = os.path.join('temp_build', 'images')
        if os.path.isdir(build_images_dir):
            shutil.rmtree(build_images_dir)
            os.makedirs(build_images_dir, exist_ok=True)

        # ── --clean-images: remove cached assets ─────────────────────────
        if args.clean_images:
            assets_dir = 'assets'
            removed = 0
            if os.path.isdir(assets_dir):
                for fname in os.listdir(assets_dir):
                    if fname.startswith('slide_') and fname.endswith('.png'):
                        os.remove(os.path.join(assets_dir, fname))
                        removed += 1
                cache_file = os.path.join(assets_dir, '.image_cache.json')
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    removed += 1
            print(f"  [Clean] Removed {removed} cached image file(s).")

        # ── Phase 3: Image Generation (BEFORE templating) ─────────────────
        try:
            from ppt_maker.imaging.image_generator import ImageGenerator
        except ImportError:
            from image_generator import ImageGenerator
        img_gen = ImageGenerator(
            images_dir=getattr(args, 'images_dir', None),
        )
        image_manifest = img_gen.generate_all(
            master_plan,
            config=config,
            force=args.force_images,
        )

        # ── Phase 4: Templating ───────────────────────────────────────────
        try:
            from ppt_maker.rendering.templater import Templater
        except ImportError:
            from templater import Templater
        templater = Templater()
        html_files = templater.generate_html(master_plan, image_manifest=image_manifest)

        # ── --preview: limit to first 3 slides ────────────────────────────
        if args.preview:
            html_files = html_files[:3]
            pdf_path = pdf_path.replace('.pdf', '_preview.pdf')
            print("  [Preview] Rendering 3 slides at half resolution.")

        # ── Phase 5: Rendering ────────────────────────────────────────────
        try:
            from ppt_maker.rendering.renderer import Renderer
        except ImportError:
            from renderer import Renderer
        renderer = Renderer(preview_mode=args.preview)

        # Only render regular PNGs when needed for audit.
        # PPTX export now uses render_background_only() separately.
        need_pngs = bool(args.audit)
        if need_pngs:
            png_files, dom_audit_results = renderer.render_all(
                html_files,
                audit=bool(args.audit),
            )
        else:
            png_files, dom_audit_results = [], []

        # ── Inline audit (if --audit flag passed to generate) ─────────────
        if args.audit and dom_audit_results:
            try:
                try:
                    from ppt_maker.audit.quality_checker import QualityChecker
                except ImportError:
                    from quality_checker import QualityChecker
                checker = QualityChecker()
                checker.run_audit(
                    slides_dir=os.path.join('temp_build', 'images'),
                    master_plan=master_plan,
                    config=config,
                    level=args.audit,
                    dom_cache_path=os.path.join('temp_build', 'dom_audit.json'),
                    output_path='design_audit.md',
                )
                print("  Audit report saved to design_audit.md")
            except ImportError:
                print("  [Info] quality_checker.py not yet implemented (Phase 4C).")

        # ── Phase 5b: Vector PDF rendering ────────────────────────────────
        # Produces text-selectable, searchable vector PDF (not a raster screenshot)
        pdf_slide_files = renderer.render_to_pdf(html_files)

        # ── Phase 6: Compilation ──────────────────────────────────────────
        try:
            from ppt_maker.export.compiler import Compiler
        except ImportError:
            from compiler import Compiler
        compiler = Compiler()

        if pdf_slide_files:
            # Use vector PDF merge (Tier 1 — selectable text)
            compiler.merge_pdfs(pdf_slide_files, pdf_path)
        elif png_files:
            # Fallback: raster PNG stitch (if vector render failed)
            print("  [Fallback] Vector PDF failed — using raster PNG compilation.")
            compiler.compile_to_pdf(png_files, pdf_path)
        else:
            # Last resort: vector render returned nothing and no PNGs were made
            # (e.g. --pptx not set so render_all was skipped). Re-run render_all.
            print("  [Fallback] Vector PDF failed — re-rendering as raster PNG.")
            fallback_pngs, _ = renderer.render_all(html_files, audit=False)
            if fallback_pngs:
                compiler.compile_to_pdf(fallback_pngs, pdf_path)
            else:
                print("  [Error] All render attempts failed — cannot produce PDF.")

        if export_notes:
            compiler.export_speaker_notes(master_plan, notes_path)

        # ── Phase 6b: PPTX Export (optional) ─────────────────────────────
        if getattr(args, 'pptx', False):
            try:
                from ppt_maker.export.pptx_exporter import PptxExporter
            except ImportError:
                from pptx_exporter import PptxExporter
            pptx_path = pdf_path.replace('.pdf', '.pptx')
            exporter = PptxExporter()

            # Render background-only slides (text hidden via CSS injection).
            # This prevents the "double text" issue where the regular PNG already
            # has text baked in AND the overlay text boxes add it again.
            # Background-only PNGs preserve all visual design (gradients, glassmorphism,
            # aurora effects, background images) but with text pixels transparent.
            bg_png_files = renderer.render_background_only(html_files)

            exporter.export(bg_png_files, master_plan, pptx_path,
                            resolved_vars=resolved_vars)


        elapsed = time.time() - run_start
        print(f"\n✓ Done in {elapsed:.1f}s")
        print(f"  PDF:   {pdf_path}")
        if getattr(args, 'pptx', False):
            print(f"  PPTX:  {pptx_path}")
        if export_notes:
            print(f"  Notes: {notes_path}")



if __name__ == "__main__":
    main()
