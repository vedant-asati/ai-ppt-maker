"""
theme_palettes.py — Curated color palette library.

Each palette is a dict of CSS variable names → values.
ThemeResolver merges these with AI-generated css_variables and user overrides.

Palette naming convention:  <structural_class>/<palette_name>
  e.g. "dark_neon/cyber_cyan", "editorial/navy"
"""

from typing import Dict, Set

# ─────────────────────────────────────────────────────────────────────────────
# PALETTES
# Four new advanced themes, each with 4–6 curated palettes.
# Existing themes (minimalist, glassmorphism, neo_brutalism, corporate_clean)
# continue to use AI-generated colors, so they are NOT in this dict.
# ─────────────────────────────────────────────────────────────────────────────

PALETTES: Dict[str, Dict[str, Dict[str, str]]] = {

    # ── Dark Neon ────────────────────────────────────────────────────────────
    # Near-black background, one electric accent color, scanline card borders.
    # Best for: Tech, AI, developer tools, gaming, cybersecurity.
    "dark_neon": {
        "cyber_cyan": {
            "--primary":        "#00FFD1",
            "--primary-rgb":    "0,255,209",
            "--text":           "#F0F0F0",
            "--text-secondary": "#888888",
            "--bg":             "#050505",
            "--bg-rgb":         "5,5,5",
            "--card-problem":   "rgba(0,0,0,0.88)",
            "--card-action":    "rgba(0,255,209,0.10)",
            "--card-positive":  "rgba(0,200,120,0.12)",
            "--text-on-dark":   "#E0E0E0",
        },
        "neon_magenta": {
            "--primary":        "#FF2D78",
            "--primary-rgb":    "255,45,120",
            "--text":           "#F0F0F0",
            "--text-secondary": "#888888",
            "--bg":             "#050505",
            "--bg-rgb":         "5,5,5",
            "--card-problem":   "rgba(0,0,0,0.88)",
            "--card-action":    "rgba(255,45,120,0.10)",
            "--card-positive":  "rgba(0,200,120,0.12)",
            "--text-on-dark":   "#E0E0E0",
        },
        "electric_blue": {
            "--primary":        "#00B4FF",
            "--primary-rgb":    "0,180,255",
            "--text":           "#F0F0F0",
            "--text-secondary": "#777777",
            "--bg":             "#040810",
            "--bg-rgb":         "4,8,16",
            "--card-problem":   "rgba(0,0,0,0.88)",
            "--card-action":    "rgba(0,180,255,0.10)",
            "--card-positive":  "rgba(0,200,120,0.12)",
            "--text-on-dark":   "#E0E0E0",
        },
        "acid_lime": {
            "--primary":        "#AAFF00",
            "--primary-rgb":    "170,255,0",
            "--text":           "#E8E8E8",
            "--text-secondary": "#666666",
            "--bg":             "#050505",
            "--bg-rgb":         "5,5,5",
            "--card-problem":   "rgba(0,0,0,0.88)",
            "--card-action":    "rgba(170,255,0,0.10)",
            "--card-positive":  "rgba(0,200,120,0.12)",
            "--text-on-dark":   "#E0E0E0",
        },
        "solar_orange": {
            "--primary":        "#FF6B00",
            "--primary-rgb":    "255,107,0",
            "--text":           "#F0F0F0",
            "--text-secondary": "#888888",
            "--bg":             "#080400",
            "--bg-rgb":         "8,4,0",
            "--card-problem":   "rgba(0,0,0,0.88)",
            "--card-action":    "rgba(255,107,0,0.10)",
            "--card-positive":  "rgba(0,200,120,0.12)",
            "--text-on-dark":   "#E0E0E0",
        },
    },

    # ── Gradient Flow ────────────────────────────────────────────────────────
    # Deep gradient background from --bg to --bg-end, glassmorphism cards.
    # Best for: Startups, SaaS, marketing, modern products.
    "gradient_flow": {
        "violet_sunset": {
            "--bg":             "#0F0C29",
            "--bg-end":         "#302B63",
            "--bg-rgb":         "15,12,41",
            "--primary":        "#6C63FF",
            "--primary-rgb":    "108,99,255",
            "--text":           "#FFFFFF",
            "--text-secondary": "rgba(255,255,255,0.65)",
            "--card-problem":   "rgba(15,12,41,0.95)",
            "--card-action":    "rgba(108,99,255,0.14)",
            "--card-positive":  "rgba(0,200,120,0.14)",
            "--text-on-dark":   "#FFFFFF",
        },
        "ocean_depth": {
            "--bg":             "#0D1B2A",
            "--bg-end":         "#1B4F72",
            "--bg-rgb":         "13,27,42",
            "--primary":        "#00C9FF",
            "--primary-rgb":    "0,201,255",
            "--text":           "#FFFFFF",
            "--text-secondary": "rgba(255,255,255,0.65)",
            "--card-problem":   "rgba(13,27,42,0.95)",
            "--card-action":    "rgba(0,201,255,0.12)",
            "--card-positive":  "rgba(0,200,120,0.14)",
            "--text-on-dark":   "#FFFFFF",
        },
        "forest_dusk": {
            "--bg":             "#0B2027",
            "--bg-end":         "#1B4332",
            "--bg-rgb":         "11,32,39",
            "--primary":        "#40C9A2",
            "--primary-rgb":    "64,201,162",
            "--text":           "#FFFFFF",
            "--text-secondary": "rgba(255,255,255,0.65)",
            "--card-problem":   "rgba(11,32,39,0.95)",
            "--card-action":    "rgba(64,201,162,0.12)",
            "--card-positive":  "rgba(0,200,120,0.14)",
            "--text-on-dark":   "#FFFFFF",
        },
        "ember_night": {
            "--bg":             "#1A0A00",
            "--bg-end":         "#3D1C00",
            "--bg-rgb":         "26,10,0",
            "--primary":        "#FF6B35",
            "--primary-rgb":    "255,107,53",
            "--text":           "#FFFFFF",
            "--text-secondary": "rgba(255,255,255,0.65)",
            "--card-problem":   "rgba(26,10,0,0.95)",
            "--card-action":    "rgba(255,107,53,0.12)",
            "--card-positive":  "rgba(0,200,120,0.14)",
            "--text-on-dark":   "#FFFFFF",
        },
    },

    # ── Editorial ────────────────────────────────────────────────────────────
    # Off-white/cream background, bold serif typography, vertical rule accents.
    # Best for: Design portfolios, journalism, academia, brand decks.
    "editorial": {
        "navy": {
            "--primary":        "#1A3A5C",
            "--primary-rgb":    "26,58,92",
            "--bg":             "#F9F6F1",
            "--bg-rgb":         "249,246,241",
            "--text":           "#111111",
            "--text-secondary": "#555555",
            "--card-problem":   "#1A2A3A",
            "--card-action":    "rgba(26,58,92,0.10)",
            "--card-positive":  "rgba(30,107,60,0.10)",
            "--text-on-dark":   "#F0EDE8",
        },
        "crimson": {
            "--primary":        "#C0392B",
            "--primary-rgb":    "192,57,43",
            "--bg":             "#F9F6F1",
            "--bg-rgb":         "249,246,241",
            "--text":           "#111111",
            "--text-secondary": "#555555",
            "--card-problem":   "#2C1010",
            "--card-action":    "rgba(192,57,43,0.10)",
            "--card-positive":  "rgba(30,107,60,0.10)",
            "--text-on-dark":   "#F0EDE8",
        },
        "forest": {
            "--primary":        "#1E6B3C",
            "--primary-rgb":    "30,107,60",
            "--bg":             "#F8F7F2",
            "--bg-rgb":         "248,247,242",
            "--text":           "#111111",
            "--text-secondary": "#555555",
            "--card-problem":   "#1A2A1A",
            "--card-action":    "rgba(30,107,60,0.10)",
            "--card-positive":  "rgba(30,107,60,0.15)",
            "--text-on-dark":   "#F0EDE8",
        },
        "terracotta": {
            "--primary":        "#CB4335",
            "--primary-rgb":    "203,67,53",
            "--bg":             "#FAF6F0",
            "--bg-rgb":         "250,246,240",
            "--text":           "#1A0E0E",
            "--text-secondary": "#5A4A4A",
            "--card-problem":   "#2C1010",
            "--card-action":    "rgba(203,67,53,0.10)",
            "--card-positive":  "rgba(30,107,60,0.10)",
            "--text-on-dark":   "#FAF0E8",
        },
        "slate": {
            "--primary":        "#2C3E50",
            "--primary-rgb":    "44,62,80",
            "--bg":             "#F5F5F5",
            "--bg-rgb":         "245,245,245",
            "--text":           "#111111",
            "--text-secondary": "#555555",
            "--card-problem":   "#1A222C",
            "--card-action":    "rgba(44,62,80,0.10)",
            "--card-positive":  "rgba(30,107,60,0.10)",
            "--text-on-dark":   "#F0EDE8",
        },
        "mustard": {
            "--primary":        "#B7950B",
            "--primary-rgb":    "183,149,11",
            "--bg":             "#FAF8F0",
            "--bg-rgb":         "250,248,240",
            "--text":           "#1A1500",
            "--text-secondary": "#5A5230",
            "--card-problem":   "#1A1400",
            "--card-action":    "rgba(183,149,11,0.12)",
            "--card-positive":  "rgba(30,107,60,0.10)",
            "--text-on-dark":   "#FAF0D8",
        },
        # INT-11: Parchment palette — matches the Panch Parivartan reference aesthetics.
        # Warm parchment bg, rust/terracotta primary, deep brown problem cards, forest green positive.
        "parchment": {
            "--primary":        "#C4531F",
            "--primary-rgb":    "196,83,31",
            "--bg":             "#F5EDD8",
            "--bg-rgb":         "245,237,216",
            "--text":           "#2C1810",
            "--text-secondary": "#6B4A35",
            "--card-bg":        "rgba(44,24,16,0.06)",
            "--card-border":    "1px solid rgba(44,24,16,0.12)",
            "--card-problem":   "#2C1810",
            "--card-action":    "#8B3820",
            "--card-positive":  "#1B5E3B",
            "--text-on-dark":   "#F5EDD8",
        },
    },

    # ── Aurora ───────────────────────────────────────────────────────────────
    # Deep dark background with two complementary aurora glow colors.
    # The aurora shimmer is a pure CSS radial-gradient (no images needed).
    # Best for: Luxury brands, premium portfolios, creative agencies, science.
    "aurora": {
        "cosmic": {
            "--aurora-1":       "#6366F1",
            "--aurora-1-rgb":   "99,102,241",
            "--aurora-2":       "#EC4899",
            "--aurora-2-rgb":   "236,72,153",
            "--primary":        "#6366F1",
            "--primary-rgb":    "99,102,241",
            "--text":           "#FAFAFA",
            "--text-secondary": "rgba(250,250,250,0.65)",
            "--bg":             "#08080F",
            "--bg-rgb":         "8,8,15",
            "--card-problem":   "rgba(8,8,15,0.92)",
            "--card-action":    "rgba(99,102,241,0.12)",
            "--card-positive":  "rgba(6,182,212,0.12)",
            "--text-on-dark":   "#F5F3FF",
        },
        "arctic": {
            "--aurora-1":       "#06B6D4",
            "--aurora-1-rgb":   "6,182,212",
            "--aurora-2":       "#8B5CF6",
            "--aurora-2-rgb":   "139,92,246",
            "--primary":        "#06B6D4",
            "--primary-rgb":    "6,182,212",
            "--text":           "#FAFAFA",
            "--text-secondary": "rgba(250,250,250,0.65)",
            "--bg":             "#05080F",
            "--bg-rgb":         "5,8,15",
            "--card-problem":   "rgba(5,8,15,0.92)",
            "--card-action":    "rgba(6,182,212,0.12)",
            "--card-positive":  "rgba(16,185,129,0.12)",
            "--text-on-dark":   "#F0FEFF",
        },
        "wildfire": {
            "--aurora-1":       "#F59E0B",
            "--aurora-1-rgb":   "245,158,11",
            "--aurora-2":       "#EF4444",
            "--aurora-2-rgb":   "239,68,68",
            "--primary":        "#F59E0B",
            "--primary-rgb":    "245,158,11",
            "--text":           "#FAFAFA",
            "--text-secondary": "rgba(250,250,250,0.65)",
            "--bg":             "#0F0800",
            "--bg-rgb":         "15,8,0",
            "--card-problem":   "rgba(15,8,0,0.92)",
            "--card-action":    "rgba(245,158,11,0.12)",
            "--card-positive":  "rgba(16,185,129,0.12)",
            "--text-on-dark":   "#FFFBF0",
        },
        "bio": {
            "--aurora-1":       "#10B981",
            "--aurora-1-rgb":   "16,185,129",
            "--aurora-2":       "#3B82F6",
            "--aurora-2-rgb":   "59,130,246",
            "--primary":        "#10B981",
            "--primary-rgb":    "16,185,129",
            "--text":           "#FAFAFA",
            "--text-secondary": "rgba(250,250,250,0.65)",
            "--bg":             "#040C08",
            "--bg-rgb":         "4,12,8",
            "--card-problem":   "rgba(4,12,8,0.92)",
            "--card-action":    "rgba(16,185,129,0.12)",
            "--card-positive":  "rgba(16,185,129,0.16)",
            "--text-on-dark":   "#F0FFF8",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Default palette per structural class (used when AI picks invalid name)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_PALETTE: Dict[str, str] = {
    "dark_neon":     "cyber_cyan",
    "gradient_flow": "violet_sunset",
    "editorial":     "navy",
    "aurora":        "cosmic",
}

# ─────────────────────────────────────────────────────────────────────────────
# Theme classification (used by audit thresholds and gradient generator)
# ─────────────────────────────────────────────────────────────────────────────

DARK_THEMES: Set[str] = {
    "dark_neon", "gradient_flow", "aurora", "glassmorphism", "neo_brutalism"
}

LIGHT_THEMES: Set[str] = {
    "editorial", "corporate_clean", "minimalist"
}

# Themes managed by ThemeResolver (palettes defined here)
PALETTE_MANAGED_THEMES: Set[str] = {
    "dark_neon", "gradient_flow", "editorial", "aurora"
}

# Themes where AI generates the CSS variables directly
AI_COLORED_THEMES: Set[str] = {
    "minimalist", "glassmorphism", "neo_brutalism", "corporate_clean"
}

# ─────────────────────────────────────────────────────────────────────────────
# Gradient generator presets (used by gradient_generator.py for offline fallbacks)
# ─────────────────────────────────────────────────────────────────────────────

GRADIENT_FALLBACK_PRESETS: Dict[str, list] = {
    # Each entry: (start_rgb, end_rgb, angle_deg, pattern)
    "dark_neon": [
        ((5, 5, 5),    (15, 15, 25), 135, "glow"),
        ((8, 4, 0),    (20, 10, 0),  135, "glow"),
        ((4, 8, 16),   (10, 20, 40), 135, "glow"),
    ],
    "gradient_flow": [
        ((15, 12, 41), (48, 43, 99),  135, "circles"),
        ((13, 27, 42), (27, 79, 114), 135, "circles"),
        ((26, 10, 0),  (61, 28, 0),   135, "circles"),
    ],
    "editorial": [
        ((249, 246, 241), (240, 236, 228), 180, "none"),
        ((248, 247, 242), (238, 236, 230), 180, "none"),
        ((250, 248, 240), (242, 238, 228), 180, "none"),
        # INT-11: Parchment palette gradients — warm cream tones
        ((245, 237, 216), (234, 222, 196), 180, "none"),
        ((240, 230, 210), (228, 214, 188), 180, "none"),
    ],
    "aurora": [
        ((8, 8, 15),  (20, 12, 35), 135, "shimmer"),
        ((5, 8, 15),  (15, 15, 40), 135, "shimmer"),
        ((15, 8, 0),  (30, 12, 5),  135, "shimmer"),
    ],
    "glassmorphism": [
        # Glassmorphism needs RICH backgrounds so the frosted glass cards stand out.
        # Near-white gradients defeat the entire glass effect.
        ((40, 80, 160),   (80, 40, 140),   135, "circles"),   # deep blue → purple
        ((20, 100, 120),  (60, 30, 100),   135, "circles"),   # teal → violet
        ((100, 40, 120),  (40, 80, 160),   135, "circles"),   # magenta → blue
        ((30, 60, 100),   (60, 120, 80),   135, "circles"),   # navy → green
    ],
    "neo_brutalism": [
        ((255, 245, 200), (255, 230, 160), 0, "grid"),
        ((200, 255, 220), (160, 240, 180), 0, "grid"),
        ((255, 220, 220), (255, 190, 190), 0, "grid"),
    ],
    "corporate_clean": [
        ((245, 248, 252), (230, 235, 245), 180, "dots"),
        ((250, 250, 252), (240, 242, 248), 135, "dots"),
    ],
    "minimalist": [
        ((252, 252, 252), (244, 244, 244), 180, "none"),
        ((248, 248, 248), (238, 238, 238), 180, "none"),
    ],
}
