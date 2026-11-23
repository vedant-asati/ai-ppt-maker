import os
import pytest
from unittest.mock import patch, MagicMock
from ppt_maker.imaging.image_generator import ImageGenerator
from ppt_maker.design.theme_resolver import ThemeResolver


def test_cloudflare_workers_ai_detection():
    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "mock_acc", "CLOUDFLARE_API_TOKEN": "mock_tok"}):
        gen = ImageGenerator(assets_dir="assets")
        assert gen.has_cloudflare is True
        assert gen.cf_account_id == "mock_acc"
        assert gen.cf_api_token == "mock_tok"


def test_cloudflare_workers_ai_generation_mock(tmp_path):
    out_file = str(tmp_path / "slide_test.png")
    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "mock_acc", "CLOUDFLARE_API_TOKEN": "mock_tok"}):
        gen = ImageGenerator(assets_dir="assets")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Valid base64 1x1 image
        mock_resp.json.return_value = {
            "result": {"image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="}
        }
        with patch("requests.post", return_value=mock_resp):
            success = gen._generate_with_cloudflare("modern architecture", out_file)
            assert success is True
            assert os.path.exists(out_file)


def test_theme_resolver_wires_slidesgo_texture():
    vars_dict, palette = ThemeResolver.resolve(
        structural_class="slidesgo_creative_watercolor",
        palette_name=None,
        ai_css_vars={},
    )
    assert "--bg-texture" in vars_dict
    assert "creative_watercolor_textures_image10.jpg" in vars_dict["--bg-texture"]

