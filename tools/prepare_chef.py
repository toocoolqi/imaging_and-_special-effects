"""One-time extraction of Classic Chef from the supplied presentation image.

Run: python tools/prepare_chef.py PATH_TO_ORIGINAL_IMAGE
Pillow is installed by Arcade. The game itself only imports Arcade.
"""
from collections import deque
from pathlib import Path
import argparse
import json

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "player"
# Coordinates refer to the supplied 1536 x 1024 image, measured from top left.
# Only the Classic Chef's idle and four WALK columns are used.
COLUMNS = {"idle": (247, 309), "down": (386, 455),
           "up": (539, 601), "left": (678, 744), "right": (820, 886)}


def cut_frame(sheet, cx, cy):
    frame = sheet.crop((cx - 28, cy - 46, cx + 28, cy + 46)).convert("RGBA")
    pixels = frame.load()
    width, height = frame.size
    # Flood only the dark blue/grey background connected to the crop boundary.
    # Brown hair, red scarf, white jacket and near-black outlines stay intact.
    pending = deque([(x, y) for x in range(width) for y in (0, height - 1)]
                    + [(x, y) for y in range(height) for x in (0, width - 1)])
    seen = set()
    while pending:
        x, y = pending.popleft()
        if (x, y) in seen or not (0 <= x < width and 0 <= y < height):
            continue
        seen.add((x, y))
        r, g, b, a = pixels[x, y]
        if a < 220 or (b >= r + 2 and g >= r and 20 <= max(r, g, b) <= 155):
            pixels[x, y] = (0, 0, 0, 0)
            pending.extend(((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    sheet = Image.open(args.source)
    if sheet.size != (1536, 1024):
        raise ValueError("This crop map requires the original 1536 x 1024 image.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {"source_size": list(sheet.size), "frame_size": [56, 92],
                "character": "Classic Chef", "frames": {}}
    preview = Image.new("RGB", (4 * 128, 5 * 216), "#e6dbc6")
    draw = ImageDraw.Draw(preview)
    for row, (direction, centers) in enumerate(COLUMNS.items()):
        manifest["frames"][direction] = []
        for i, (cx, cy) in enumerate((x, y) for y in (181, 281) for x in centers):
            frame = cut_frame(sheet, cx, cy)
            name = f"{direction}_{i}.png"
            frame.save(OUTPUT / name)
            manifest["frames"][direction].append({"file": name, "center": [cx, cy]})
            enlarged = frame.resize((112, 184), Image.Resampling.NEAREST)
            preview.paste(enlarged, (i * 128 + 8, row * 216 + 24), enlarged)
            draw.text((i * 128 + 8, row * 216 + 5), name, fill="#23303c")
    (OUTPUT / "frames.json").write_text(json.dumps(manifest, indent=2) + "\n")
    preview.save(OUTPUT / "frame_preview.png")
    print(f"Prepared 20 frames in {OUTPUT}")


if __name__ == "__main__":
    main()
