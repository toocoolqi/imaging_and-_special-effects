"""Prepare game assets from the two supplied presentation sheets (Pillow).

Usage: python tools/prepare_kitchen.py KITCHEN_JPEG ITEMS_JPEG
This is a one-time crop utility; the Arcade game uses the prepared PNGs.
Coordinates below are top-left image pixels, not game coordinates.
"""
import argparse
from collections import deque
import json
from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "kitchen"
KITCHEN_CROPS = {
    "back_wall": (0, 0, 1408, 270),
    "floor_tile": (620, 250, 714, 294),
    "stove": (174, 478, 391, 686),
    "bin": (651, 524, 757, 670),
    "table": (967, 502, 1253, 676),
    "board": (315, 167, 388, 202),
}
ITEM_CROPS = {
    "sandwich": (32, 159, 160, 300),
    "tomato": (181, 168, 289, 280),
    "noodles": (311, 167, 439, 288),
    "milk": (466, 138, 563, 291),
    "crate_sandwich": (607, 128, 772, 343),
    "crate_tomato": (766, 128, 932, 343),
    "crate_noodles": (927, 128, 1096, 343),
    "crate_milk": (1090, 128, 1256, 343),
    "plate": (62, 462, 445, 722),
    "pot": (521, 495, 753, 682),
}


def remove_edge_background(image, *, light):
    """Flood only the sheet background connected to a crop edge.

    Keep dark outlines and enclosed white plate/food pixels. No generative art
    or redrawing is used: all visible prop pixels come from the supplied sheets.
    """
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    pending = deque([(x, y) for x in range(width) for y in (0, height - 1)]
                    + [(x, y) for y in range(height) for x in (0, width - 1)])
    seen = set()
    while pending:
        x, y = pending.popleft()
        if (x, y) in seen or not (0 <= x < width and 0 <= y < height):
            continue
        seen.add((x, y))
        r, g, b, _ = pixels[x, y]
        is_background = (r > 210 and g > 205 and b > 187) if light else (
            15 <= r <= 49 and 20 <= g <= 54 and 24 <= b <= 60
            and max(r, g, b) - min(r, g, b) < 19)
        if is_background:
            pixels[x, y] = (0, 0, 0, 0)
            pending.extend(((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
    # Discard disconnected pixels from adjacent pictures/shadows at crop edges.
    components = []
    seen.clear()
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y][3] == 0:
                continue
            component, pending = set(), deque([(x, y)])
            while pending:
                px, py = pending.popleft()
                if (px, py) in seen or not (0 <= px < width and 0 <= py < height):
                    continue
                seen.add((px, py))
                if pixels[px, py][3]:
                    component.add((px, py))
                    pending.extend(((px-1, py), (px+1, py), (px, py-1), (px, py+1)))
            components.append(component)
    keep = max(components, key=len, default=set())
    for component in components:
        if component is not keep:
            for x, y in component:
                pixels[x, y] = (0, 0, 0, 0)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kitchen", type=Path)
    parser.add_argument("items", type=Path)
    args = parser.parse_args()
    kitchen, items = Image.open(args.kitchen), Image.open(args.items)
    if kitchen.size != (1408, 768) or items.size != (1280, 853):
        raise ValueError("Use the original 1408x768 tiled kitchen and 1280x853 item sheets.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prepared = {}
    for name, bounds in KITCHEN_CROPS.items():
        crop = kitchen.crop(bounds).convert("RGBA")
        if name in ("stove", "bin", "table"):
            crop = remove_edge_background(crop, light=True)
        crop.save(OUTPUT / f"{name}.png")
        prepared[name] = crop
    for name, bounds in ITEM_CROPS.items():
        crop = remove_edge_background(items.crop(bounds), light=False)
        crop.save(OUTPUT / f"{name}.png")
        prepared[name] = crop
    preview = Image.new("RGB", (800, 4 * 180), "#c8c3b5")
    draw = ImageDraw.Draw(preview)
    for i, (name, crop) in enumerate(prepared.items()):
        crop.thumbnail((184, 145), Image.Resampling.NEAREST)
        x, y = i % 4 * 200, i // 4 * 180
        preview.paste(crop, (x + (200-crop.width)//2, y + 22), crop)
        draw.text((x+8, y+4), name, fill="#242b2e")
    preview.save(OUTPUT / "asset_preview.png")
    (OUTPUT / "crops.json").write_text(json.dumps({
        "kitchen_sheet_size": kitchen.size, "items_sheet_size": items.size,
        "kitchen_crops": KITCHEN_CROPS, "item_crops": ITEM_CROPS,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(prepared)} kitchen assets in {OUTPUT}")


if __name__ == "__main__":
    main()
