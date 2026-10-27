"""Validated color conversion, harmony, contrast and gradient mathematics."""
from __future__ import annotations

import colorsys
import math
import random
import re

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
CSS_NAMES = {
    "black": "#000000", "white": "#FFFFFF", "red": "#FF0000", "green": "#008000",
    "blue": "#0000FF", "navy": "#000080", "teal": "#008080", "cyan": "#00FFFF",
    "purple": "#800080", "orange": "#FFA500", "gold": "#FFD700", "pink": "#FFC0CB",
    "coral": "#FF7F50", "slategray": "#708090", "rebeccapurple": "#663399",
}


def normalize_hex(value: str) -> str:
    match = HEX_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("Enter a six-digit HEX color, such as #8B5CF6.")
    return "#" + match.group(1).upper()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = normalize_hex(value)
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    if len(rgb) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in rgb):
        raise ValueError("RGB channels must be integers from 0 to 255.")
    return "#%02X%02X%02X" % rgb


def hsv(value: str) -> tuple[int, int, int]:
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in hex_to_rgb(value)))
    return round(h * 360) % 360, round(s * 100), round(v * 100)


def hsl(value: str) -> tuple[int, int, int]:
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in hex_to_rgb(value)))
    return round(h * 360) % 360, round(s * 100), round(l * 100)


def from_hsv(h: float, s: float, v: float) -> str:
    return rgb_to_hex(tuple(round(x * 255) for x in colorsys.hsv_to_rgb((h % 360) / 360, max(0, min(s, 100)) / 100, max(0, min(v, 100)) / 100)))


def from_hsl(h: float, s: float, l: float) -> str:
    return rgb_to_hex(tuple(round(x * 255) for x in colorsys.hls_to_rgb((h % 360) / 360, max(0, min(l, 100)) / 100, max(0, min(s, 100)) / 100)))


def cmyk(value: str) -> tuple[int, int, int, int]:
    r, g, b = (x / 255 for x in hex_to_rgb(value))
    k = 1 - max(r, g, b)
    if k == 1:
        return 0, 0, 0, 100
    return tuple(round(x * 100) for x in ((1-r-k)/(1-k), (1-g-k)/(1-k), (1-b-k)/(1-k), k))


def closest_name(value: str) -> str:
    rgb = hex_to_rgb(value)
    name = min(CSS_NAMES, key=lambda n: sum((a-b)**2 for a, b in zip(rgb, hex_to_rgb(CSS_NAMES[n]))))
    return name if normalize_hex(value) == CSS_NAMES[name] else f"Near {name}"


def luminance(value: str) -> float:
    channels = [c / 255 for c in hex_to_rgb(value)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(a*b for a, b in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def harmony(base: str, kind: str, count: int = 5) -> list[str]:
    h, s, v = hsv(base)
    count = max(3, min(10, count))
    angles = {
        "Complementary": [0, 180], "Analogous": [-30, -15, 0, 15, 30],
        "Triadic": [0, 120, 240], "Tetradic": [0, 90, 180, 270],
        "Split complementary": [0, 150, 210],
    }
    if kind == "Monochromatic":
        return [from_hsv(h, s, 25 + i * 65 / (count - 1)) for i in range(count)]
    if kind == "Shades and tints":
        return [from_hsl(h, s, 15 + i * 70 / (count - 1)) for i in range(count)]
    if kind == "Random harmonized":
        h = random.randrange(360)
        return [from_hsv(h + (i - count//2)*18, max(25, min(95, s + random.randrange(-15, 16))), max(35, min(95, v + random.randrange(-15, 16)))) for i in range(count)]
    offsets = angles.get(kind)
    if offsets is None:
        raise ValueError("Unknown harmony model.")
    return [normalize_hex(base) if i == 0 else from_hsv(h + offsets[i % len(offsets)], s, max(30, min(100, v + (i // len(offsets))*12))) for i in range(count)]


def interpolate(stops: list[dict], position: float) -> str:
    ordered = sorted(stops, key=lambda item: item["position"])
    if position <= ordered[0]["position"]:
        return normalize_hex(ordered[0]["color"])
    if position >= ordered[-1]["position"]:
        return normalize_hex(ordered[-1]["color"])
    for left, right in zip(ordered, ordered[1:]):
        if left["position"] <= position <= right["position"]:
            span = right["position"] - left["position"]
            t = (position - left["position"]) / span if span else 0
            return rgb_to_hex(tuple(round(a + (b-a)*t) for a, b in zip(hex_to_rgb(left["color"]), hex_to_rgb(right["color"]))))
    return normalize_hex(ordered[-1]["color"])


def gradient_image(width: int, height: int, stops: list[dict], kind: str, angle: float):
    from PIL import Image
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    palette = [hex_to_rgb(interpolate(stops, i / 10)) for i in range(1001)]
    radians = math.radians(angle)
    dx, dy = math.cos(radians), math.sin(radians)
    extent = (abs(dx)*width + abs(dy)*height) / 2 or 1
    for y in range(height):
        for x in range(width):
            if kind == "Radial":
                position = min(100, math.hypot((x-width/2)/(width/2), (y-height/2)/(height/2))*100)
            else:
                position = max(0, min(100, 50 + ((x-width/2)*dx + (y-height/2)*dy) / extent * 50))
            pixels[x, y] = palette[round(position * 10)]
    return image
