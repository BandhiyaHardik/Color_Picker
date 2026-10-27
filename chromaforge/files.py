"""Image analysis and palette import/export."""
from __future__ import annotations

import json
from pathlib import Path
import re

from PIL import Image

from .color_math import normalize_hex, rgb_to_hex, hex_to_rgb


def extract_colors(path: str, count: int) -> tuple[list[dict], Image.Image]:
    with Image.open(path) as source:
        if source.format not in {"PNG", "JPEG", "WEBP", "BMP"}:
            raise ValueError("Choose a PNG, JPEG, WebP or BMP image.")
        preview = source.convert("RGBA")
        preview.thumbnail((720, 480))
        analysis = source.convert("RGBA")
        analysis.thumbnail((400, 400))
        visible = [(r,g,b) for r,g,b,a in analysis.get_flattened_data() if a > 0]
        if not visible:
            raise ValueError("This image contains no visible pixels.")
        opaque = Image.new("RGB", (len(visible), 1))
        opaque.putdata(visible)
        quantized = opaque.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()
        counts = sorted(quantized.getcolors() or [], reverse=True)
        total = sum(n for n, _ in counts) or 1
        colors = []
        for amount, index in counts[:count]:
            rgb = tuple(palette[index*3:index*3+3])
            colors.append({"hex": rgb_to_hex(rgb), "percent": round(amount / total * 100, 1)})
        return colors, preview


def validate_palette_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The selected file is not valid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("colors"), list) or not 2 <= len(data["colors"]) <= 20:
        raise ValueError("Palette JSON needs a colors array with 2–20 HEX colors.")
    colors = [normalize_hex(item) for item in data["colors"]]
    return {"name": str(data.get("name", "Imported palette"))[:80], "colors": colors,
            "harmony_type": "Imported", "is_favorite": False}


def export_palette(path: str, name: str, colors: list[str]):
    colors = [normalize_hex(c) for c in colors]
    suffix = Path(path).suffix.lower()
    slug = [re.sub(r"[^a-z0-9]+", "-", f"{name}-{i+1}".lower()).strip("-") for i in range(len(colors))]
    if suffix == ".json":
        content = json.dumps({"name": name, "colors": colors}, indent=2)
    elif suffix == ".css":
        content = ":root {\n" + "\n".join(f"  --{s}: {c};" for s, c in zip(slug, colors)) + "\n}\n"
    elif suffix == ".scss":
        content = "\n".join(f"${s}: {c};" for s, c in zip(slug, colors)) + "\n"
    elif suffix == ".gpl":
        content = "GIMP Palette\nName: " + name + "\nColumns: 5\n#\n" + "\n".join(f"{r:3} {g:3} {b:3} {s}" for (r,g,b),s in zip(map(hex_to_rgb, colors),slug)) + "\n"
    elif suffix == ".png":
        image = Image.new("RGB", (max(300, len(colors)*100), 160))
        for x in range(image.width):
            index = min(len(colors)-1, x * len(colors) // image.width)
            for y in range(image.height):
                image.putpixel((x,y), hex_to_rgb(colors[index]))
        image.save(path)
        return
    elif suffix == ".txt":
        content = "\n".join(colors) + "\n"
    else:
        raise ValueError("Choose JSON, CSS, SCSS, TXT, GPL or PNG.")
    Path(path).write_text(content, encoding="utf-8")
