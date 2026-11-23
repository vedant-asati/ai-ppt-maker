"""
extract_slidesgo_assets.py — Extracts, categorizes, and indexes media assets and theme metadata
from SlidesGo PPTX files.
"""

import os
import glob
import zipfile
import re
import json
import xml.etree.ElementTree as ET
from PIL import Image
import io

INPUT_DIR = "/home/intruder-jsr/exps/ai-ppt-maker/temp/slidesgoppts"
OUTPUT_DIR = "/home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/assets/slidesgo"
METADATA_FILE = os.path.join(OUTPUT_DIR, "themes_metadata.json")

def sanitize_name(name: str) -> str:
    name = os.path.splitext(name)[0]
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '_', name)
    name = re.sub(r'_by_slidesgo.*', '', name)
    name = re.sub(r'_style.*', '', name)
    return name.strip('_')

def analyze_deck(pptx_path: str):
    deck_name = sanitize_name(os.path.basename(pptx_path))
    print(f"\nProcessing deck: {deck_name} ({os.path.basename(pptx_path)})")
    
    with zipfile.ZipFile(pptx_path) as z:
        # 1. Fonts and Colors from theme
        theme_colors = []
        if 'ppt/theme/theme1.xml' in z.namelist():
            root = ET.fromstring(z.read('ppt/theme/theme1.xml'))
            for elem in root.iter():
                if elem.tag.endswith('srgbClr'):
                    c = '#' + elem.attrib.get('val', '').upper()
                    if c not in theme_colors:
                        theme_colors.append(c)

        # 2. Actual Fonts used in slides
        slide_fonts = set()
        for name in z.namelist():
            if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                xml_text = z.read(name).decode('utf-8', errors='ignore')
                for m in re.finditer(r'typeface="([^"]+)"', xml_text):
                    f = m.group(1).strip()
                    if not f.startswith('+') and f not in ('Arial', 'Calibri'):
                        slide_fonts.add(f)

        # 3. Media Assets
        media_names = [n for n in z.namelist() if n.startswith('ppt/media/')]
        extracted_media = []

        for m_name in media_names:
            data = z.read(m_name)
            ext = os.path.splitext(m_name)[1].lower()
            if ext not in ('.png', '.jpg', '.jpeg', '.svg'):
                continue

            try:
                img = Image.open(io.BytesIO(data))
                w, h = img.size
                is_transparent = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
                aspect = w / max(1, h)

                # Classify asset
                if ext in ('.jpg', '.jpeg') or (w >= 1200 and h >= 700):
                    category = "textures"
                elif is_transparent and (w < 800 or h < 800):
                    category = "doodles"
                else:
                    category = "shapes"

                out_filename = f"{deck_name}_{category}_{os.path.basename(m_name)}"
                out_path = os.path.join(OUTPUT_DIR, category, out_filename)
                with open(out_path, 'wb') as f_out:
                    f_out.write(data)

                extracted_media.append({
                    "filename": out_filename,
                    "rel_path": f"slidesgo/{category}/{out_filename}",
                    "category": category,
                    "width": w,
                    "height": h,
                    "is_transparent": is_transparent
                })
            except Exception as e:
                # If PIL cannot open SVG or corrupt image, save raw
                category = "shapes"
                out_filename = f"{deck_name}_{category}_{os.path.basename(m_name)}"
                out_path = os.path.join(OUTPUT_DIR, category, out_filename)
                with open(out_path, 'wb') as f_out:
                    f_out.write(data)
                extracted_media.append({
                    "filename": out_filename,
                    "rel_path": f"slidesgo/{category}/{out_filename}",
                    "category": category,
                    "width": 0,
                    "height": 0,
                    "is_transparent": False
                })

        print(f"  Extracted {len(extracted_media)} media assets")
        print(f"  Slide Fonts: {list(slide_fonts)}")
        print(f"  Theme Colors: {theme_colors[:6]}")

        return {
            "deck_id": deck_name,
            "original_filename": os.path.basename(pptx_path),
            "fonts": sorted(list(slide_fonts)),
            "palette": theme_colors[:6],
            "media": extracted_media
        }

def main():
    os.makedirs(os.path.join(OUTPUT_DIR, "textures"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "doodles"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "shapes"), exist_ok=True)

    pptx_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.pptx")))
    print(f"Found {len(pptx_files)} PPTX files to process.")

    all_metadata = {}
    for p in pptx_files:
        info = analyze_deck(p)
        all_metadata[info["deck_id"]] = info

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

    total_media = sum(len(d["media"]) for d in all_metadata.values())
    print(f"\nSuccessfully extracted and indexed {total_media} media assets across {len(all_metadata)} decks.")
    print(f"Metadata saved to: {METADATA_FILE}")

if __name__ == "__main__":
    main()

