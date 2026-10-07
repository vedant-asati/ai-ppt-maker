# Gemini API — Available Models & Rate Limits (Free Tier)
# Captured: 2026-07-26
# Project: Gemini Project (free tier)
#
# Use this as a reference when choosing models in the pipeline.
# Models with 0/0/0 limits are NOT available on the free tier.

# ═══════════════════════════════════════════════════════════════════════════════
# TEXT-OUT MODELS (generateContent — text + vision input → text output)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model Name                  │ API Model ID                    │ RPM │ TPM    │ RPD
# ────────────────────────────┼─────────────────────────────────┼─────┼────────┼──────
# Gemini 2.5 Flash            │ gemini-2.5-flash                │  5  │ 250K   │  20    ← CURRENT: planner.py
# Gemini 2.5 Flash Lite       │ gemini-2.5-flash-lite           │ 10  │ 250K   │  20
# Gemini 3 Flash              │ gemini-3-flash-preview          │  5  │ 250K   │  20
# Gemini 3.1 Flash Lite       │ gemini-3.1-flash-lite           │ 15  │ 250K   │ 500    ← BEST for bulk (highest RPD)
# Gemini 3.5 Flash            │ gemini-3.5-flash                │  5  │ 250K   │  20
# Gemini 3.5 Flash Lite       │ gemini-3.5-flash-lite           │ 15  │ 250K   │ 500    ← BEST for bulk (highest RPD)
# Gemini 3.6 Flash            │ gemini-3.6-flash                │  5  │ 250K   │  20    ← LATEST
#
# NOT AVAILABLE (0 limits):
#   Gemini 2 Flash, Gemini 2 Flash Lite, Gemini 2.5 Pro, Gemini 3.1 Pro

# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-MODAL GENERATIVE MODELS (image/audio/video generation)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model Name                              │ API Model ID                    │ RPM │ TPM  │ RPD
# ────────────────────────────────────────┼─────────────────────────────────┼─────┼──────┼──────
# Gemini 2.5 Flash TTS                    │ gemini-2.5-flash-preview-tts    │  3  │ 10K  │  10
# Gemini 3.1 Flash TTS                    │ gemini-3.1-flash-tts            │  3  │ 10K  │  10
# Imagen 4 Fast Generate                  │ imagen-4-fast-generate          │  -  │  -   │  25
# Imagen 4 Generate                       │ imagen-4-generate               │  -  │  -   │  25
# Imagen 4 Ultra Generate                 │ imagen-4-ultra-generate         │  -  │  -   │  25
#
# NOT AVAILABLE (0 limits):
#   Nano Banana (Gemini 2.5 Flash Image), Nano Banana 2 (Gemini 3.1 Flash Image),
#   Nano Banana 2 Lite, Gemini Omni Flash, Lyria 3, Veo 3

# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION MODELS (for slide images)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model Name                  │ API Model ID                    │ RPD │ Notes
# ────────────────────────────┼─────────────────────────────────┼─────┼──────────────
# Gemini 3.1 Flash Image      │ gemini-3.1-flash-image          │  0  │ CURRENT: image_generator.py (NOT AVAILABLE!)
# Imagen 4 Fast               │ imagen-4-fast-generate          │ 25  │ Available, fast
# Imagen 4                    │ imagen-4-generate               │ 25  │ Available, high quality
# Imagen 4 Ultra              │ imagen-4-ultra-generate         │ 25  │ Available, highest quality

# ═══════════════════════════════════════════════════════════════════════════════
# OTHER MODELS
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model Name                  │ API Model ID                    │ RPM │ TPM  │ RPD
# ────────────────────────────┼─────────────────────────────────┼─────┼──────┼──────
# Gemini Embedding 1          │ gemini-embedding-001            │ 100 │ 30K  │ 1K
# Gemini Embedding 2          │ gemini-embedding-002            │ 100 │ 30K  │ 1K
# Gemma 4 26B                 │ gemma-4-26b                     │  30 │ 16K  │ 14.4K
# Gemma 4 31B                 │ gemma-4-31b                     │  30 │ 16K  │ 14.4K
# Gemini Robotics ER 1.5      │ gemini-robotics-er-1.5-preview  │  10 │ 250K │  20
# Gemini Robotics ER 1.6      │ gemini-robotics-er-1.6-preview  │   5 │ 250K │  20

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE API (streaming/dialog)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model Name                              │ RPM       │ TPM  │ RPD
# ────────────────────────────────────────┼───────────┼──────┼──────
# Gemini 2.5 Flash Native Audio Dialog    │ Unlimited │ 1M   │ Unlimited
# Gemini 3 Flash Live                     │ Unlimited │ 65K  │ Unlimited
# Gemini 3.5 Live Translate               │ Unlimited │ 20K  │ Unlimited

# ═══════════════════════════════════════════════════════════════════════════════
# RECOMMENDATIONS FOR THIS PROJECT
# ═══════════════════════════════════════════════════════════════════════════════
#
# Use Case               │ Recommended Model           │ Reason
# ────────────────────────┼─────────────────────────────┼──────────────────────
# Planner (text gen)      │ gemini-3.1-flash-lite       │ 500 RPD, cheapest
# Image Matcher (vision)  │ gemini-3.1-flash-lite       │ 500 RPD, supports vision
# Quality Audit (vision)  │ gemini-3.5-flash-lite       │ 500 RPD, newer model
# Image Generation        │ imagen-4-fast-generate      │ 25 RPD, actual image gen
# Embeddings              │ gemini-embedding-002        │ 1K RPD, latest

# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS (.env)
# ═══════════════════════════════════════════════════════════════════════════════
#
# GEMINI_API_KEY     — Primary key (free tier)
# GEMINI_API_KEY_2   — Secondary key (free tier, separate project)
#
# Each key has its OWN independent quota. Two keys = 2x effective limits.
# Use `api_keys.get_api_keys()` to load all available keys.
# Use `api_keys.get_client()` for a client with automatic key rotation on 429.
