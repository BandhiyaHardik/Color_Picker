import pytest

from chromaforge.color_math import (normalize_hex, hex_to_rgb, rgb_to_hex, hsv, hsl,
                                    from_hsv, from_hsl, contrast, harmony, interpolate)
from chromaforge.files import validate_palette_json, extract_colors, export_palette
from PIL import Image


def test_hex_rgb_roundtrip():
    assert hex_to_rgb("#8B5CF6") == (139, 92, 246)
    assert rgb_to_hex((139, 92, 246)) == "#8B5CF6"
    with pytest.raises(ValueError): normalize_hex("#xyz")


def test_hsv_hsl_roundtrip():
    for color in ("#000000", "#FFFFFF", "#8B5CF6", "#06B6D4"):
        h, s, v = hsv(color)
        result = hex_to_rgb(from_hsv(h,s,v))
        assert all(abs(a-b) <= 3 for a,b in zip(result,hex_to_rgb(color)))
        h, s, l = hsl(color)
        result = hex_to_rgb(from_hsl(h,s,l))
        assert all(abs(a-b) <= 3 for a,b in zip(result,hex_to_rgb(color)))


def test_contrast_thresholds():
    assert contrast("#000000", "#FFFFFF") == pytest.approx(21)
    assert contrast("#777777", "#777777") == pytest.approx(1)


def test_harmony_and_gradient_interpolation():
    assert harmony("#FF0000", "Complementary", 4)[0] == "#FF0000"
    assert len(harmony("#8B5CF6", "Analogous", 5)) == 5
    assert interpolate([{"color":"#000000","position":0},{"color":"#FFFFFF","position":100}],50) == "#808080"


def test_palette_json_validation():
    assert validate_palette_json('{"colors":["#112233","#AABBCC"]}')["colors"] == ["#112233","#AABBCC"]
    with pytest.raises(ValueError): validate_palette_json('{"colors":["bad"]}')


def test_image_extraction_ignores_transparent_pixels(tmp_path):
    path = tmp_path / "sample.png"
    image = Image.new("RGBA", (2, 1))
    image.putdata([(255, 0, 0, 255), (0, 0, 255, 0)])
    image.save(path)
    colors, _ = extract_colors(str(path), 3)
    assert colors == [{"hex": "#FF0000", "percent": 100.0}]


def test_palette_export_contains_actual_colors(tmp_path):
    path = tmp_path / "palette.css"
    export_palette(str(path), "My Palette", ["#123456", "#ABCDEF"])
    output = path.read_text(encoding="utf-8")
    assert "#123456" in output and "#ABCDEF" in output
