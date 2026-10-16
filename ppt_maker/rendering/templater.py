import os
import jinja2
from pathlib import Path
try:
    from ppt_maker.core.schemas import MasterPlan
except ImportError:
    from schemas import MasterPlan

# Resolve paths relative to package and project root
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
_PROJECT_ROOT = os.path.dirname(_PKG_ROOT)


def _resolve_templates_dir(custom_dir=None):
    if custom_dir and os.path.isdir(custom_dir):
        return custom_dir
    # 1. Check ppt_maker/templates
    pkg_tmpl = os.path.join(_PKG_ROOT, 'templates')
    if os.path.isdir(pkg_tmpl):
        return pkg_tmpl
    # 2. Check project root templates/
    root_tmpl = os.path.join(_PROJECT_ROOT, 'templates')
    if os.path.isdir(root_tmpl):
        return root_tmpl
    # 3. Fallback
    return os.path.join(_HERE, 'templates')


# INT-01: Map slide_purpose → body CSS tone class
# Injected as second body class so base.html tone-* rules fire per slide
_PURPOSE_TO_TONE = {
    'problem_statement': 'tone-problem',
    'challenge':         'tone-problem',
    'pain_point':        'tone-problem',
    'evidence':          'tone-evidence',
    'data':              'tone-evidence',
    'social_proof':      'tone-evidence',
    'call_to_action':    'tone-action',
    'cta':               'tone-action',
    'solution':          'tone-action',
    'next_steps':        'tone-action',
}

class Templater:
    def __init__(self, templates_dir=None, build_dir='temp_build'):
        self.build_dir = build_dir
        os.makedirs(self.build_dir, exist_ok=True)

        resolved_templates = _resolve_templates_dir(templates_dir)
        template_loader = jinja2.FileSystemLoader(searchpath=resolved_templates)
        # Fix #28: enable autoescape so slide content with <, >, & doesn't break HTML layout
        self.env = jinja2.Environment(loader=template_loader, autoescape=True)

    def generate_html(self, master_plan: MasterPlan, image_manifest: dict = None):
        print("Templater: Generating HTML files from Master Plan...")
        html_files = []
        total_slides = len(master_plan.slides)
        image_manifest = image_manifest or {}

        # Detect offline font bundle
        local_fonts_available = (
            os.path.exists(os.path.join(_PROJECT_ROOT, 'assets', 'fonts', 'fonts.css')) or
            os.path.exists(os.path.join('assets', 'fonts', 'fonts.css'))
        )

        for slide in master_plan.slides:
            # Determine template name based on layout_type
            template_name = f"{slide.layout_type}.html"

            try:
                template = self.env.get_template(template_name)
            except jinja2.exceptions.TemplateNotFound:
                print(f"Warning: Template {template_name} not found. Falling back to generic.html")
                template = self.env.get_template("generic.html")

            # Build image context from manifest.
            # IMPORTANT: convert to standard RFC 8089 file:// URI via Path.as_uri()
            # so the browser can resolve the path cross-platform (Windows & Linux).
            img_info = image_manifest.get(slide.slide_number, {})
            raw_image_path = img_info.get('path', '')
            if raw_image_path and os.path.isfile(raw_image_path):
                image_path = Path(raw_image_path).resolve().as_uri()
                has_image  = True
            else:
                image_path = ''
                has_image  = False
            image_status = img_info.get('status', 'none')  # api|cache|fallback|user|none
            image_role   = img_info.get('role', getattr(slide, 'image_role', 'background') or 'background')

            # INT-01: Derive semantic card tone class from slide_purpose
            card_tone = _PURPOSE_TO_TONE.get(
                (getattr(slide, 'slide_purpose', None) or '').lower(),
                ''
            )

            html_content = template.render(
                slide=slide,
                theme=master_plan.theme,
                total_slides=total_slides,
                has_image=has_image,
                image_path=image_path,
                image_status=image_status,
                image_role=image_role,
                card_tone=card_tone,                # INT-01: semantic body class
                local_fonts_available=local_fonts_available,
            )

            out_path = os.path.join(self.build_dir, f"slide_{slide.slide_number:03d}.html")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            html_files.append(out_path)

        print(f"Templater: Successfully generated {len(html_files)} HTML files in {self.build_dir}/")
        return html_files
