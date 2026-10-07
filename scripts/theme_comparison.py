"""
theme_comparison.py — Deep visual analysis across all themes.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import subprocess

THEMES_TO_TEST = {
    "dark_neon": {
        "--bg": "#050505", "--bg-rgb": "5,5,5", "--primary": "#00FFD1",
        "--primary-rgb": "0,255,209", "--text": "#F0F0F0", "--text-secondary": "#888888",
    },
    "gradient_flow": {
        "--bg": "#0F0C29", "--bg-rgb": "15,12,41", "--bg-end": "#302B63",
        "--primary": "#6C63FF", "--primary-rgb": "108,99,255",
        "--text": "#FFFFFF", "--text-secondary": "rgba(255,255,255,0.65)",
    },
    "aurora": {
        "--bg": "#08080F", "--bg-rgb": "8,8,15", "--primary": "#A78BFA",
        "--primary-rgb": "167,139,250", "--text": "#F5F3FF",
        "--text-secondary": "rgba(245,243,255,0.65)",
        "--aurora-1": "#A78BFA", "--aurora-1-rgb": "167,139,250",
        "--aurora-2": "#06B6D4", "--aurora-2-rgb": "6,182,212",
    },
    "editorial": {
        "--bg": "#F9F6F1", "--bg-rgb": "249,246,241", "--primary": "#1A1A2E",
        "--primary-rgb": "26,26,46", "--text": "#1A1A2E", "--text-secondary": "#4A4A6A",
    },
    "glassmorphism_AI_light": {
        "--bg": "#F7FAFC", "--bg-rgb": "247,250,252", "--primary": "#2B6CB0",
        "--primary-rgb": "43,108,176", "--text": "#1A202C", "--text-secondary": "#4A5568",
    },
    "glassmorphism_FIXED": {
        "--bg": "#31363F", "--bg-rgb": "49,54,63", "--primary": "#2B6CB0",
        "--primary-rgb": "43,108,176", "--text": "#F0F0F0",
        "--text-secondary": "rgba(255,255,255,0.65)", "--card-bg": "rgba(255,255,255,0.08)",
    },
}

KEY_SLIDES = [0, 1, 4, 7, 8]
SLIDE_LABELS = ["cover", "generic", "quote", "split", "stat"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(ROOT, "temp_build")
OUTPUT_DIR = os.path.join(ROOT, "scripts", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

THUMB_W = 480
THUMB_H = 270
LABEL_H = 40
GAP = 6
HEADER_H = 60


def build_override_css(vars_dict, structural_class):
    vars_css = " ".join(f"{k}: {v} !important;" for k, v in vars_dict.items())
    body_bg = vars_dict.get("--bg", "#050505")
    body_bg_end = vars_dict.get("--bg-end", body_bg)
    return f"""
    :root {{ {vars_css} }}
    html, body {{ {vars_css} background-color: {body_bg} !important; color: {vars_dict.get('--text','#F0F0F0')} !important; }}
    """


def quality_metrics(img):
    pts = [(int(img.width*x), int(img.height*y)) for x in [.1,.3,.5,.7,.9] for y in [.1,.3,.5,.7,.9]]
    colors = [img.getpixel(p)[:3] for p in pts]
    avg_b = sum(sum(c)/3 for c in colors)/len(colors)
    cr = max(sum(c)/3 for c in colors) - min(sum(c)/3 for c in colors)
    unique = len(set((c[0]//20*20, c[1]//20*20, c[2]//20*20) for c in colors))
    return {"avg_brightness": round(avg_b,1), "color_range": round(cr,1), "unique_clusters": unique,
            "score": min(100, int(cr/2.4 + unique*3))}


def render_themed_slides(theme_name, vars_dict):
    html_files = sorted(os.path.join(HTML_DIR, f) for f in os.listdir(HTML_DIR)
                        if f.startswith("slide_") and f.endswith(".html"))
    key_files = [html_files[i] for i in KEY_SLIDES if i < len(html_files)]
    structural_class = "glassmorphism" if "glassmorphism" in theme_name else theme_name.split("_")[0]
    override_css = build_override_css(vars_dict, structural_class)
    images = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()
        for html_file in key_files:
            url = f"file://{os.path.abspath(html_file)}"
            try: page.goto(url, wait_until="networkidle", timeout=15000)
            except: page.goto(url, wait_until="domcontentloaded", timeout=8000)
            try: page.evaluate("document.fonts.ready")
            except: time.sleep(0.3)
            page.add_style_tag(content=override_css)
            page.evaluate(f"document.body.className = '{structural_class}'")
            time.sleep(0.1)
            out_path = os.path.join(OUTPUT_DIR, f"{theme_name}_{os.path.basename(html_file).replace('.html','.png')}")
            page.screenshot(path=out_path)
            images.append(Image.open(out_path))
        browser.close()
    return images


def extract_pdf_pages(pdf_path, pages=(1,2), dpi=96):
    results = {}
    for page_n in pages:
        prefix = os.path.join(OUTPUT_DIR, f"_tmp_p{page_n}_{os.path.basename(pdf_path)}")
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-f", str(page_n), "-l", str(page_n), pdf_path, prefix], capture_output=True)
        files = sorted(f for f in os.listdir(OUTPUT_DIR) if f.startswith(f"_tmp_p{page_n}_{os.path.basename(pdf_path)}"))
        if files:
            fp = os.path.join(OUTPUT_DIR, files[0])
            results[page_n] = Image.open(fp).copy()
            os.remove(fp)
    return results


def get_font(size=12, bold=False):
    paths = [f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if bold else ''}.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()


def build_comparison_grid(all_results):
    themes = list(all_results.keys())
    n_cols = len(SLIDE_LABELS)
    n_rows = len(themes)
    theme_label_w = 190
    col_w = THUMB_W + GAP
    row_h = THUMB_H + LABEL_H + GAP
    total_w = theme_label_w + col_w * n_cols + GAP * 2
    total_h = HEADER_H + row_h * n_rows + GAP * 2

    grid = Image.new("RGB", (total_w, total_h), (15, 15, 22))
    draw = ImageDraw.Draw(grid)
    font_hd = get_font(22, bold=True)
    font_md = get_font(13, bold=True)
    font_sm = get_font(11)

    draw.text((10, 14), "THEME × SLIDE LAYOUT — QUALITY COMPARISON", fill=(200,210,255), font=font_hd)

    # Column headers
    for col, label in enumerate(SLIDE_LABELS):
        x = theme_label_w + col * col_w + GAP + 4
        draw.text((x, 46), label.upper(), fill=(140,150,200), font=font_md)

    THEME_COLORS = {
        "dark_neon": (5, 25, 25), "gradient_flow": (10, 8, 35),
        "aurora": (8, 5, 25), "editorial": (45, 38, 25),
        "glassmorphism_AI_light": (35, 15, 15), "glassmorphism_FIXED": (10, 28, 45),
    }

    for row, theme_name in enumerate(themes):
        y_base = HEADER_H + row * row_h + GAP
        lbl_bg = THEME_COLORS.get(theme_name, (25, 25, 35))
        label_img = Image.new("RGB", (theme_label_w - GAP, THUMB_H + LABEL_H), lbl_bg)
        ld = ImageDraw.Draw(label_img)
        short = theme_name.replace("_"," ").upper()
        ld.text((8, 12), short, fill=(200,210,240), font=font_md)

        imgs = all_results.get(theme_name, [])
        if imgs:
            m_avg = sum(quality_metrics(im)["score"] for im in imgs) / len(imgs)
            bar_color = (50,200,80) if m_avg>=60 else (200,150,40) if m_avg>=30 else (200,60,60)
            bw = int((theme_label_w-GAP) * min(m_avg,100)/100)
            ld.rectangle([8, THUMB_H+LABEL_H-8, 8+bw, THUMB_H+LABEL_H-4], fill=bar_color)
            ld.text((8, THUMB_H+16), f"avg Q={m_avg:.0f}/100", fill=(140,160,180), font=font_sm)

        grid.paste(label_img, (GAP, y_base))

        for col, img in enumerate(imgs):
            x = theme_label_w + col * col_w + GAP
            y = y_base
            thumb = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
            grid.paste(thumb, (x, y))
            m = quality_metrics(img)
            bar_color = (50,200,80) if m["score"]>=60 else (200,150,40) if m["score"]>=30 else (200,60,60)
            bw = int(THUMB_W * min(m["score"],100)/100)
            draw.rectangle([x, y+THUMB_H, x+bw, y+THUMB_H+4], fill=bar_color)
            draw.text((x+2, y+THUMB_H+6), f"Q={m['score']}  br={m['avg_brightness']:.0f}  rng={m['color_range']:.0f}", fill=(130,140,170), font=font_sm)

    return grid


def build_before_after(historic_results, new_results):
    # historic_results: {label: {1: cover_img, 2: content_img}}
    # new_results:      {theme_name: [cover_img, ...]}
    items = []
    for label, pages in sorted(historic_results.items()):
        if 1 in pages:
            items.append((f"HISTORIC: {label}", pages[1]))
    for theme_name, imgs in new_results.items():
        if imgs:
            items.append((f"NEW: {theme_name}", imgs[0]))

    n = len(items)
    n_cols = 3
    n_rows = (n + n_cols - 1) // n_cols
    pad = 8
    cell_w = THUMB_W + pad
    cell_h = THUMB_H + LABEL_H + pad
    total_w = n_cols * cell_w + pad
    total_h = HEADER_H + n_rows * cell_h + pad

    img_out = Image.new("RGB", (total_w, total_h), (15, 15, 22))
    draw = ImageDraw.Draw(img_out)
    font_hd = get_font(20, bold=True)
    font_md = get_font(12, bold=True)
    font_sm = get_font(10)

    draw.text((pad, pad), "COVER SLIDE — HISTORIC vs NEW (all themes)", fill=(200,210,255), font=font_hd)

    for idx, (label, cover_img) in enumerate(items):
        col = idx % n_cols
        row = idx // n_cols
        x = pad + col * cell_w
        y = HEADER_H + row * cell_h

        thumb = cover_img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        img_out.paste(thumb, (x, y))

        m = quality_metrics(cover_img)
        bar_color = (50,200,80) if m["score"]>=60 else (200,150,40) if m["score"]>=30 else (200,60,60)
        bw = int(THUMB_W * min(m["score"],100)/100)
        draw.rectangle([x, y+THUMB_H, x+bw, y+THUMB_H+4], fill=bar_color)

        short = label[:42]
        draw.text((x+2, y+THUMB_H+6), short, fill=(180,190,220), font=font_md)
        draw.text((x+2, y+THUMB_H+20), f"Q={m['score']}  brightness={m['avg_brightness']:.0f}  range={m['color_range']:.0f}", fill=(120,130,160), font=font_sm)

    return img_out


def main():
    print("="*65)
    print("THEME COMPARISON ANALYSIS")
    print("="*65)
    analysis = {}

    print("\n[1/4] Extracting historic test PDF pages...")
    historic_results = {}
    test_dir = os.path.join(ROOT, "test_output")
    for d in sorted(os.listdir(test_dir)):
        dp = os.path.join(test_dir, d)
        if not os.path.isdir(dp): continue
        for f in os.listdir(dp):
            if f.endswith(".pdf"):
                print(f"  {d}...")
                pages = extract_pdf_pages(os.path.join(dp, f), pages=(1, 2), dpi=96)
                historic_results[d] = pages
                for pg_n, img in pages.items():
                    m = quality_metrics(img)
                    analysis[f"HIST_{d}_p{pg_n}"] = m
                    print(f"    page {pg_n}: Q={m['score']} br={m['avg_brightness']} rng={m['color_range']}")

    print("\n[2/4] Rendering new themed slides...")
    new_results = {}
    for theme_name, vars_dict in THEMES_TO_TEST.items():
        print(f"\n  {theme_name}...")
        try:
            imgs = render_themed_slides(theme_name, vars_dict)
            new_results[theme_name] = imgs
            for slide_label, im in zip(SLIDE_LABELS[:len(imgs)], imgs):
                m = quality_metrics(im)
                analysis[f"NEW_{theme_name}_{slide_label}"] = m
                status = "✓" if m["score"]>=40 else "⚠"
                print(f"    {slide_label:<8}: Q={m['score']:3d}  br={m['avg_brightness']:5.1f}  rng={m['color_range']:5.1f}  {status}")
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback; traceback.print_exc()
            new_results[theme_name] = []

    print("\n[3/4] Building comparison grid...")
    grid = build_comparison_grid(new_results)
    grid_path = os.path.join(OUTPUT_DIR, "comparison_grid.png")
    grid.save(grid_path)
    print(f"  → {grid_path}")

    print("\n[4/4] Building before/after cover comparison...")
    ba = build_before_after(historic_results, new_results)
    ba_path = os.path.join(OUTPUT_DIR, "before_after_cover.png")
    ba.save(ba_path)
    print(f"  → {ba_path}")

    with open(os.path.join(OUTPUT_DIR, "theme_analysis.json"), "w") as f:
        json.dump(analysis, f, indent=2)

    print("\n" + "="*65)
    print("QUALITY SUMMARY (sorted by score desc)")
    print("="*65)
    print(f"{'Key':<55} {'Q':>4} {'Br':>6} {'Rng':>6}")
    print("-"*75)
    for key, m in sorted(analysis.items(), key=lambda x: -x[1]["score"])[:30]:
        status = "✓" if m["score"]>=40 else "⚠"
        print(f"{key:<55} {m['score']:>4}  {m['avg_brightness']:>5.0f}  {m['color_range']:>5.0f}  {status}")

    print(f"\n✓ Done. Outputs in: {OUTPUT_DIR}/")
    print(f"  comparison_grid.png, before_after_cover.png, theme_analysis.json")

if __name__ == "__main__":
    main()
