"""Build the four kitchen art sets from the warm source art (Pillow only).

Run from the repository root:

    python -m tools.build_kitchens

Output: assets/kitchen/<map_id>/ for warm_clean, warm_overgrown, metal_clean
and metal_damaged, each with the SAME file names, plus
assets/kitchen/manifest.json. The original pictures in assets/kitchen/ are
only read. Fixed random seeds make every run produce identical files. The
game itself never imports Pillow for this; it only loads the PNGs.

Every file is stored on the game's art grid: one image pixel is one pixel of
the 608 x 352 canvas in restaurant/pixel_art.py (two world pixels), so the
game draws it 1:1 with no resampling.

Pipeline
1. room.png: floor, walls, rear upstands and flat decoration are painted at
   world resolution from the same geometry as restaurant/kitchen/details.py,
   reduced to the art grid, then the condition's damage is painted at art
   resolution.
2. Furniture and wall sprites: each source sprite is resized once to four
   times its art-grid size. Clean warm = that base. Every variant is computed
   from the same base, details are drawn in 4x4 blocks (one art pixel), and
   the result is reduced 4:1, so silhouettes match exactly.
   - metal: HSV masks find wood and teal paint -> luminance ramp to steel ->
     brushed grain; the dining room through the hatch is tinted instead.
   - overgrown: rot patches, chipped paint, damp streaks, mould, moss, vines.
   - damaged (on metal): grime, rust on edges and seams, drips, dents,
     scratches, a door hanging off its hinge.
"""
import json
from math import pi
from pathlib import Path
import random

from PIL import Image, ImageChops, ImageDraw

from restaurant.kitchen.days import DAYS, MAP_IDS
from restaurant.kitchen.layout import (
    BOTTOM_WALL_HEIGHT, FLOOR_TOP, KITCHEN_HEIGHT, KITCHEN_WIDTH, PROPS, SIDE_WALL_WIDTH,
    WALL_ART,
)
from tools import kitchen_fx as fx

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "kitchen"
OUTPUT = ROOT / "assets" / "kitchen"
ART = 2          # world pixels per art pixel (restaurant.pixel_art.PIXEL_SIZE)
DETAIL = 4       # working pixels per art pixel while processing sprites

# Sprite name -> (source file, crop box (left, top, width, height) or None).
SOURCES = {
    "table": ("table.png", None),
    "stove": ("stove.png", None),
    "bin": ("bin.png", None),
    "sink": ("restaurant_details.png", (124, 58, 578, 271)),
    "pass_counter": ("restaurant_details.png", (803, 108, 634, 222)),
    "spice_shelf": ("restaurant_details.png", (178, 395, 501, 250)),
    "extractor": ("restaurant_details.png", (841, 371, 550, 277)),
    "clean_board": ("restaurant_details.png", (199, 738, 440, 197)),
    "service_hatch": ("restaurant_details.png", (816, 686, 612, 267)),
}
# The dark dining room visible through the hatch (fractions of the sprite).
HATCH_WINDOW = (0.095, 0.165, 0.908, 0.75)
COUNTERS = {"sink", "pass_counter", "table"}
SHARED_FOOD_ART = {"crate_sandwich", "crate_tomato", "crate_noodles", "crate_milk", "plate", "pot"}
# Cabinet door that has fallen off: (left, top, width, height) as fractions.
BROKEN_DOORS = {"sink": (0.085, 0.57, 0.17, 0.33), "pass_counter": (0.645, 0.56, 0.125, 0.33)}


def art_size(width, height):
    """Size on the art grid, rounded exactly as the game snaps sprites."""
    return round(width / ART), round(height / ART)


def display_sizes():
    """World size of each sprite, read from the day layouts (single source)."""
    sizes = {}
    for day in DAYS:
        items = [(p.asset, p.width, p.height) for p in day.props if p.asset not in SHARED_FOOD_ART]
        items += [(name, w, h) for name, _, _, w, h in WALL_ART]
        for name, w, h in items:
            if sizes.setdefault(name, (w, h)) != (w, h):
                raise ValueError(f"{name} must have one size in every kitchen")
    return sizes


def load_base(name, world_size):
    file, crop = SOURCES[name]
    image = Image.open(SOURCE / file).convert("RGBA")
    if crop:
        left, top, width, height = crop
        image = image.crop((left, top, left + width, top + height))
    w, h = art_size(*world_size)
    return fx.resize_rgba(image, (w * DETAIL, h * DETAIL), Image.LANCZOS)


def finish(image):
    """Reduce a processed sprite 4:1 onto the art grid."""
    return fx.resize_rgba(image, (image.width // DETAIL, image.height // DETAIL), Image.BOX)


def window_mask(name, image):
    mask = Image.new("L", image.size, 0)
    if name == "service_hatch":
        w, h = image.size
        l, t, r, b = HATCH_WINDOW
        ImageDraw.Draw(mask).rectangle((int(l * w), int(t * h), int(r * w), int(b * h)), fill=255)
    return mask


def seed_for(name, salt):
    return sum(map(ord, name)) * 101 + salt


def clip_overlay(out, overlay, mask, original):
    overlay.putalpha(ImageChops.multiply(overlay.getchannel("A"), mask))
    return fx.keep_alpha(Image.alpha_composite(out, overlay), original)

# --------------------------------------------------------------------------
# Furniture transforms (working resolution: DETAIL pixels per art pixel)
# --------------------------------------------------------------------------


def metalize(name, image):
    if name == "clean_board":
        return image  # a wooden board on steel stays instantly recognisable
    window = window_mask(name, image)
    outside = ImageChops.invert(window)
    alpha = fx.solid_alpha(image)
    wood = fx.mask_and(fx.wood_mask(image), outside)
    paint = fx.mask_and(fx.paint_mask(image), outside)
    outline = fx.mask_and(fx.outline_mask(image), outside)
    # Already-grey parts (hood, hob, basin) lean warm; cool them to match.
    neutral = fx.mask_and(fx.hsv_mask(image, ((0, 360),), max_s=110, min_v=50), alpha, outside,
                          ImageChops.invert(wood), ImageChops.invert(paint))
    out = fx.adjust(image, neutral, saturation=0.3, tint=(150, 162, 176), tint_amount=0.14)
    out = fx.ramp_recolor(out, (70, 78, 88), (236, 240, 244), wood, lo=40, hi=175)
    out = fx.ramp_recolor(out, (48, 56, 66), (170, 182, 194), paint, lo=40, hi=150)
    out = fx.brushed_streaks(out, fx.mask_or(wood, paint), seed_for(name, 1), scale=DETAIL)
    out = fx.adjust(out, outline, saturation=0.15, tint=(30, 36, 46), tint_amount=0.35)
    # The dining room beyond the hatch becomes a cool blue bistro.
    out = fx.adjust(out, fx.mask_and(window, alpha), saturation=0.6,
                    tint=(40, 56, 110), tint_amount=0.28)
    return out


def _vine_layer(name, image, rng):
    """Vines climbing from the feet and draping from the front lip."""
    layer = fx.pixel_layer(image.size, DETAIL)
    draw = ImageDraw.Draw(layer)
    w, h = layer.size
    bounds = (0, 0, w, h)
    if name in COUNTERS or name == "stove":
        for x in (rng.randint(2, max(3, w // 6)), rng.randint(w * 5 // 6, w - 3)):
            fx.draw_vine(draw, (x, h - 2), -pi / 2, int(h * rng.uniform(0.4, 0.62)), rng,
                         leaf_every=4, bounds=bounds)
            fx.draw_ivy(draw, (x, h - 4), 6, 6, rng, bounds)
    if name in COUNTERS:
        lip = int(h * (0.36 if name == "table" else 0.44))
        for x in rng.sample(range(w // 6, w * 5 // 6), 2):
            fx.draw_vine(draw, (x, lip), pi / 2, int(h * rng.uniform(0.25, 0.42)), rng,
                         leaf_every=4, wobble=0.3, bounds=bounds)
    if name in ("spice_shelf", "service_hatch", "extractor"):
        count = 3 if name == "service_hatch" else 2
        for x in rng.sample(range(4, w - 4), count):
            fx.draw_vine(draw, (x, 1), pi / 2, int(h * rng.uniform(0.35, 0.7)), rng,
                         leaf_every=4, wobble=0.35, bounds=bounds)
        fx.draw_ivy(draw, (rng.choice((4, w - 6)), 4), 8, 10, rng, bounds)
    if name == "bin":
        fx.draw_vine(draw, (w // 3, h - 2), -pi / 2, int(h * 0.55), rng, leaf_every=4, bounds=bounds)
    return fx.enlarge(layer, image.size)


def overgrow(name, image):
    seed = seed_for(name, 20)
    rng = random.Random(seed)
    size = image.size
    alpha = fx.solid_alpha(image)
    outside = ImageChops.invert(window_mask(name, image))
    wood = fx.mask_and(fx.wood_mask(image), outside)
    paint = fx.mask_and(fx.paint_mask(image), outside)
    keep_clear = Image.new("L", size, 0)
    if name == "clean_board":  # keep the cutting surface itself clean and legible
        w, h = size
        ImageDraw.Draw(keep_clear).rectangle((w * 0.12, h * 0.15, w * 0.88, h * 0.85), fill=255)
    usable = fx.mask_and(alpha, ImageChops.invert(keep_clear))

    # 1. Rotting wood: soft patches go darker, greyer and slightly green.
    field = fx.value_noise(size, 34, seed)
    rot = fx.mask_and(fx.blocky(fx.threshold(field, 138, 168), DETAIL), wood, usable)
    out = fx.adjust(image, rot, brightness=0.8, saturation=0.5, tint=(96, 88, 58), tint_amount=0.22)
    core = fx.mask_and(fx.blocky(fx.threshold(field, 186), DETAIL), wood, usable)
    out = fx.adjust(out, core, brightness=0.7, saturation=0.4, tint=(62, 56, 38), tint_amount=0.3)
    out = fx.adjust(out, wood, saturation=0.82, brightness=0.95)
    holes = fx.mask_and(fx.blocky(fx.threshold(fx.value_noise(size, 6, seed + 9, 1), 222), DETAIL), core)
    out = fx.fill(out, (48, 36, 28), holes)                    # wood-worm holes
    # 2. Faded, chipped teal paint showing bare wood underneath.
    out = fx.adjust(out, paint, saturation=0.6, brightness=0.9, tint=(146, 152, 118), tint_amount=0.14)
    chips = fx.mask_and(fx.blocky(fx.threshold(fx.value_noise(size, 12, seed + 1, 1), 190), DETAIL), paint)
    out = fx.fill(out, (128, 96, 66), chips)
    rim = fx.mask_and(ImageChops.subtract(fx.dilate(chips, DETAIL // 2), chips), paint)
    out = fx.multiply(out, (130, 130, 118), rim)
    # 3. Damp streaks running down from the worktop.
    w, h = size
    rng_rows = random.Random(seed + 2)
    streak_grid = Image.new("L", (max(2, w // (DETAIL * 2)), 6))
    streak_grid.putdata([rng_rows.randrange(256) for _ in range(streak_grid.width * 6)])
    streaks = streak_grid.resize(size, Image.BILINEAR)
    damp = fx.mask_and(fx.threshold(streaks, 175, 230), fx.vertical_bias(size, 0.1, 1.0), usable)
    out = fx.multiply(out, (188, 178, 146), fx.blocky(damp, DETAIL))
    # 4. A few clustered mould specks, and moss along the bottom edge.
    specks = fx.mask_and(fx.threshold(fx.value_noise(size, 6, seed + 3, 1), 216),
                         fx.threshold(fx.value_noise(size, 30, seed + 4), 158), usable)
    out = fx.fill(out, (52, 66, 44), fx.blocky(specks, DETAIL))
    bottom = fx.mask_and(fx.edge_band(image, DETAIL * 2), fx.vertical_bias(size, -1.0, 1.0), usable)
    moss = fx.mask_and(fx.blocky(fx.threshold(fx.value_noise(size, 8, seed + 5, 1), 120), DETAIL), bottom)
    out = fx.fill(out, fx.LEAF_DARK, moss)
    moss_light = fx.mask_and(moss, fx.blocky(fx.threshold(fx.value_noise(size, 6, seed + 6, 1), 160), DETAIL))
    out = fx.fill(out, fx.LEAF_MID, moss_light)
    # 5. Vines, clipped to the original silhouette (no new floor obstacles).
    if name != "clean_board":
        out = clip_overlay(out, _vine_layer(name, image, rng), alpha, image)
    return out


def damage_metal(name, image):
    seed = seed_for(name, 40)
    rng = random.Random(seed)
    size = image.size
    alpha = fx.solid_alpha(image)
    outside = ImageChops.invert(window_mask(name, image))
    usable = fx.mask_and(alpha, outside)
    # 1. Grime collects low down.
    out = fx.multiply(image, (204, 196, 184), fx.mask_and(fx.vertical_bias(size, -0.3, 0.8), usable))
    layer = fx.pixel_layer(size, DETAIL)
    draw = ImageDraw.Draw(layer)
    shade = fx.pixel_layer(size, DETAIL)
    shade_draw = ImageDraw.Draw(shade)
    lw, lh = layer.size
    if name == "clean_board":
        for _ in range(10):  # knife scores
            x, y = rng.randint(lw // 6, lw * 5 // 6), rng.randint(lh // 5, lh * 4 // 5)
            draw.line((x, y, x + rng.randint(2, 4), y), fill=(92, 58, 34, 210))
        return clip_overlay(out, fx.enlarge(layer, size), alpha, image)
    # 2. Rust where water sits: silhouette edges and panel seams, in patches,
    #    plus a few blooms on flat steel. Kept chunky, not speckled.
    seams = fx.dilate(fx.outline_mask(image), DETAIL // 2)
    edges = fx.edge_band(image, DETAIL * 2)
    active = fx.threshold(fx.value_noise(size, 30, seed, 2), 166)
    bloom = fx.threshold(fx.value_noise(size, 46, seed + 1, 1), 228)
    rust = fx.mask_or(fx.mask_and(fx.mask_or(seams, edges), active), bloom)
    rust = fx.mask_and(fx.blocky(rust, DETAIL), usable)
    halo = fx.mask_and(ImageChops.subtract(fx.dilate(rust, DETAIL), rust), usable)
    out = fx.multiply(out, (214, 176, 142), fx.blocky(halo, DETAIL))     # rusty water stain
    out = fx.keep_alpha(Image.alpha_composite(out, fx.rust_colors(size, rust, seed + 3, block=DETAIL)),
                        image)
    # 3. Rust drips run downward from rusty pixels.
    small_rust = rust.resize((lw, lh), Image.NEAREST)
    rusty = [(x, y) for y in range(lh) for x in range(lw) if small_rust.getpixel((x, y)) > 0]
    for x, y in rng.sample(rusty, min(len(rusty), max(2, lw // 14))):
        length = rng.randint(2, 6)
        for k in range(length):
            if y + k < lh:
                draw.point((x, y + k), fill=fx.RUST[1 if k < length // 2 else 0] + (max(80, 220 - k * 24),))
    # 4. Dents on the steel fronts: dark upper-left rim, light lower-right rim.
    for _ in range(max(1, lw * lh // 1200)):
        cx, cy = rng.randint(lw // 8, lw * 7 // 8), rng.randint(lh // 2, lh * 7 // 8)
        rx = rng.randint(2, 4)
        fx.dent(shade_draw, draw, cx, cy, rx, max(2, int(rx * rng.uniform(0.6, 0.9))))
    # 5. A few scratches: a light gouge with a dark lower lip.
    for _ in range(max(2, lw // 24)):
        x, y = rng.randint(1, lw - 6), rng.randint(lh // 6, lh - 3)
        dx = rng.randint(2, 5)
        draw.line((x, y, x + dx, y + rng.choice((-1, 1))), fill=(238, 242, 246, 160))
    # 6. Broken panels: a door hanging off its hinge, cracked oven glass,
    #    a split island panel.
    if name in BROKEN_DOORS:
        fl, ft, fw, fh = BROKEN_DOORS[name]
        x0, y0, dw, dh = int(fl * lw), int(ft * lh), int(fw * lw), int(fh * lh)
        draw.rectangle((x0, y0, x0 + dw, y0 + dh), fill=(18, 20, 24, 255))        # dark interior
        draw.line((x0 + 1, y0 + dh // 2, x0 + dw - 1, y0 + dh // 2), fill=(58, 64, 72, 255))  # shelf
        door = [(x0 - 1, y0 + 2), (x0 + dw - 1, y0 + 4), (x0 + dw - 3, y0 + dh + 3), (x0 - 3, y0 + dh + 1)]
        draw.polygon(door, fill=(142, 152, 162, 255), outline=(44, 50, 58, 255))
        draw.line((door[0], door[1]), fill=(226, 232, 238, 255))
    elif name == "stove":
        cx, cy = int(lw * 0.52), int(lh * 0.8)
        for angle in (-2.6, -1.2, -0.3, 0.6, 2.2):
            fx.draw_crack(draw, (cx, cy), angle, rng.randint(3, 6), rng, (214, 222, 230, 230), None, 0.1)
        draw.point((cx, cy), fill=(20, 22, 26, 255))
    elif name == "table":
        fx.draw_crack(draw, (int(lw * 0.3), int(lh * 0.66)), 0.35, int(lw * 0.3), rng,
                      (26, 28, 32, 255), (206, 212, 220, 200), 0.4)
    for overlay in (fx.enlarge(shade, size), fx.enlarge(layer, size)):
        out = clip_overlay(out, overlay, usable, image)
    return out

# --------------------------------------------------------------------------
# Room background: paint at world resolution (y up, like Arcade)
# --------------------------------------------------------------------------

INK = (65, 49, 43)
WARM = dict(
    grout=(173, 156, 124), tile_a=(224, 207, 168), tile_b=(231, 214, 177), tile_hi=(239, 223, 190),
    motif_a=(154, 174, 145), motif_b=(197, 148, 108), side=(104, 70, 52), side_hi=(210, 156, 99),
    trim=(174, 111, 70), trim_hi=(210, 156, 99), splash=(238, 220, 181), splash_line=(212, 189, 151),
    stripe_dark=(54, 88, 79), stripe=(92, 139, 126), board=(54, 88, 79), board_frame=(174, 111, 70),
    chalk=(189, 207, 173), clock=(238, 220, 181), plinth=(174, 111, 70), plinth_edge=(123, 87, 59),
    plinth_hi=(210, 156, 99), mat=(110, 126, 105), mat_edge=(89, 105, 86), mat_detail=(139, 151, 124),
    splash_row=28, splash_brick=40, ink=INK,
)
METAL = dict(
    grout=(122, 130, 136), tile_a=(198, 204, 208), tile_b=(184, 191, 196), tile_hi=(214, 219, 223),
    motif_a=(170, 178, 184), motif_b=(170, 178, 184), side=(62, 68, 76), side_hi=(154, 164, 174),
    trim=(118, 128, 138), trim_hi=(184, 194, 202), splash=(232, 236, 238), splash_line=(196, 203, 208),
    stripe_dark=(34, 58, 100), stripe=(66, 106, 164), board=(44, 50, 56), board_frame=(150, 160, 170),
    chalk=(212, 222, 228), clock=(236, 240, 242), plinth=(132, 142, 150), plinth_edge=(84, 92, 100),
    plinth_hi=(196, 204, 210), mat=(54, 58, 62), mat_edge=(36, 38, 42), mat_detail=(30, 32, 35),
    splash_row=14, splash_brick=28, ink=(38, 42, 48),
)
MATS = ((48, 436, 166), (273, 431, 118), (638, 434, 212))


class WorldPainter:
    def __init__(self, background):
        self.image = Image.new("RGB", (KITCHEN_WIDTH, KITCHEN_HEIGHT), background)
        self.draw = ImageDraw.Draw(self.image)
        self.grout = Image.new("L", self.image.size, 0)
        self.grout_draw = ImageDraw.Draw(self.grout)

    def rect(self, x, y, w, h, color, target=None):
        x, y, w, h = int(x), int(y), int(w), int(h)
        if w > 0 and h > 0:
            box = (x, KITCHEN_HEIGHT - (y + h), x + w - 1, KITCHEN_HEIGHT - y - 1)
            (target or self.draw).rectangle(box, fill=color)

    def frame(self, x, y, w, h, color, edge, thickness=2):
        self.rect(x, y, w, h, edge)
        self.rect(x + thickness, y + thickness, w - thickness * 2, h - thickness * 2, color)


def paint_room(style):
    """Same geometry as kitchen/details.py room_details(), without its marks."""
    p = METAL if style.startswith("metal") else WARM
    W, H, top = KITCHEN_WIDTH, KITCHEN_HEIGHT, FLOOR_TOP
    art = WorldPainter(p["ink"])
    r, f = art.rect, art.frame
    r(18, 18, W - 36, top - 18, p["grout"])
    r(18, 18, W - 36, top - 18, 255, target=art.grout_draw)
    for y in range(20, top - 2, 32):
        for x in range(20, W - 20, 32):
            shade = p["tile_a"] if (x // 32 + y // 32) % 2 else p["tile_b"]
            width, height = min(30, W - 20 - x), min(30, top - 2 - y)
            r(x, y, width, height, shade)
            r(x, y, width, height, 0, target=art.grout_draw)
            r(x, y + height - 2, width, 2, p["tile_hi"])
            if p is WARM and x % 128 == 20 and y % 128 == 20 and height >= 24:
                color = p["motif_a"] if (x + y) % 256 == 40 else p["motif_b"]
                r(x + 12, y + 6, 6, 18, color)
                r(x + 6, y + 12, 18, 6, color)
                r(x + 12, y + 12, 6, 6, shade)
            elif p is METAL and (x // 32 + y // 32) % 2 and height >= 24:
                for dx, dy in ((8, 8), (20, 8), (8, 20), (20, 20)):   # anti-slip studs
                    r(x + dx, y + dy, 2, 2, p["motif_a"])
    for x in (0, W - 18):
        r(x, 0, 18, H, p["side"])
        r(x + 4, 18, 10, H - 24, p["side_hi"])
    r(18, 0, W - 36, 18, p["trim"])
    r(18, 14, W - 36, 4, p["trim_hi"])
    r(18, top, W - 36, H - top - 12, p["splash"])
    row, brick = p["splash_row"], p["splash_brick"]
    for y in range(top + 8, 692, row):
        r(18, y, W - 36, 2, p["splash_line"])
        offset = brick // 2 if ((y - top - 8) // row) % 2 else 0
        for x in range(20 + offset, W - 20, brick):
            r(x, y, 2, min(row, 692 - y), p["splash_line"])
    r(18, top, W - 36, 5, p["stripe_dark"])
    r(18, top + 5, W - 36, 3, p["stripe"])
    for prop in PROPS:   # rear upstands behind equipment fitted to the wall
        if prop.fixed_to_back_wall:
            x = prop.x - prop.width / 2
            bottom = int(prop.y + prop.height / 2) - 4
            r(x, bottom, prop.width, top - bottom, p["stripe_dark"])
            r(x + 4, bottom + 2, prop.width - 8, top - bottom - 4, p["splash"])
            r(x + 4, bottom + 2, prop.width - 8, 4, p["trim"])
            for seam in range(int(x) + 32, int(x + prop.width) - 4, 32):
                r(seam, bottom + 6, 2, max(2, top - bottom - 8), p["trim_hi"])
    r(18, 692, W - 36, 12, p["trim"])
    r(18, 692, W - 36, 4, p["trim_hi"])
    f(894, 649, 30, 30, p["clock"], p["ink"], thickness=4)
    r(908, 663, 2, 9, p["ink"])
    r(908, 661, 8, 2, p["ink"])
    f(522, 625, 60, 56, p["board"], p["board_frame"], thickness=4)
    for y, length in ((666, 35), (657, 40), (648, 30), (639, 36)):
        r(532, y, length, 2, p["chalk"])
    f(50, 38, 370, 18, p["plinth"], p["plinth_edge"])
    for x in (64, 154, 244, 334):
        r(x, 44, 52, 5, p["plinth_hi"])
    for x, y, w in MATS:
        f(x, y, w, 24, p["mat"], p["mat_edge"])
        if p is WARM:
            for stripe in range(x + 6, x + w - 4, 8):
                r(stripe, y + 4, 2, 16, p["mat_detail"])
        else:
            for hx in range(x + 6, x + w - 6, 8):
                for hy in (y + 6, y + 14):
                    r(hx, hy, 4, 4, p["mat_detail"])
    return art

# --------------------------------------------------------------------------
# Room damage, painted at art resolution (PIL coordinates, y down)
# --------------------------------------------------------------------------


class ArtRoom:
    """The room reduced to the art grid, plus helpers in art pixels."""

    def __init__(self, painter):
        size = (KITCHEN_WIDTH // ART, KITCHEN_HEIGHT // ART)
        self.image = painter.image.resize(size, Image.NEAREST).convert("RGBA")
        self.grout = painter.grout.resize(size, Image.NEAREST)
        self.W, self.H = size
        side, bottom = SIDE_WALL_WIDTH // ART, BOTTOM_WALL_HEIGHT // ART
        self.floor_box = (side, self.row(FLOOR_TOP) , self.W - side - 1, self.H - bottom - 1)
        self.splash_box = (side, self.row(692), self.W - side - 1, self.row(FLOOR_TOP) - 1)

    def row(self, world_y):
        return (KITCHEN_HEIGHT - world_y) // ART

    def point(self, world_x, world_y):
        return int(world_x) // ART, int(KITCHEN_HEIGHT - world_y) // ART

    def mask(self, box):
        mask = Image.new("L", self.image.size, 0)
        ImageDraw.Draw(mask).rectangle(box, fill=255)
        return mask


def overgrow_room(room, points, seed=7):
    rng = random.Random(seed)
    img, size, W, H = room.image, room.image.size, room.W, room.H
    x0, y0, x1, y1 = room.floor_box
    floor, splash = room.mask(room.floor_box), room.mask(room.splash_box)
    walls = ImageChops.invert(floor)
    near_wall = ImageChops.subtract(floor, fx.erode(floor, 16))
    # 1. Damp stains: stepped tones from a soft, noisy blob.
    damp_cores = Image.new("L", size, 0)
    for _ in range(8):
        soft = fx.soft_blob(size, (rng.randint(x0 + 25, x1 - 25), rng.randint(y0 + 20, y1 - 20)),
                            (rng.randint(22, 48), rng.randint(13, 26)), rng.randrange(99999), cell=8)
        light = fx.mask_and(fx.threshold(soft, 74), floor)
        dark = fx.mask_and(fx.threshold(soft, 132), floor)
        img = fx.multiply(img, (228, 218, 186), light)
        img = fx.multiply(img, (214, 204, 170), dark)
        img = fx.multiply(img, (208, 196, 160), ImageChops.subtract(light, fx.erode(light, 1)))
        damp_cores = fx.mask_or(damp_cores, dark)
    # 2. Moss in the grout near walls and inside damp patches; clumps by walls.
    grout_moss = fx.mask_and(room.grout, fx.mask_or(near_wall, damp_cores),
                             fx.threshold(fx.value_noise(size, 3, seed + 2, 1), 96))
    img = fx.fill(img, (98, 124, 66), grout_moss)
    clump_zone = ImageChops.subtract(floor, fx.erode(floor, 10))
    clumps = fx.mask_and(fx.threshold(fx.value_noise(size, 5, seed + 3, 2), 146), clump_zone)
    img = fx.fill(img, fx.LEAF_DARK, clumps)
    img = fx.fill(img, fx.LEAF_MID, fx.mask_and(clumps, fx.threshold(fx.value_noise(size, 2, seed + 4, 1), 138)))
    img = fx.fill(img, fx.LEAF_LIGHT, fx.mask_and(clumps, fx.threshold(fx.value_noise(size, 2, seed + 5, 1), 214)))
    # 3. Backsplash: yellowed, damp streaks from the ceiling, mould clusters.
    img = fx.multiply(img, (236, 224, 188), splash)
    streak_grid = Image.new("L", (W // 3, 4))
    streak_grid.putdata([rng.randrange(256) for _ in range(streak_grid.width * 4)])
    streaks = fx.threshold(streak_grid.resize(size, Image.BILINEAR), 170, 225)
    img = fx.multiply(img, (196, 182, 142), fx.mask_and(streaks, splash, fx.vertical_bias(size, 1.0, -2.2)))
    mould = fx.mask_and(fx.threshold(fx.value_noise(size, 2, seed + 6, 1), 196),
                        fx.threshold(fx.value_noise(size, 22, seed + 7), 168), splash)
    img = fx.fill(img, (86, 100, 70), mould)
    # 4. Rotting wood trim on side walls, skirting and ceiling rail.
    trim = fx.mask_and(walls, ImageChops.invert(splash))
    trim_rot = fx.mask_and(trim, fx.threshold(fx.value_noise(size, 8, seed + 8), 150))
    img = fx.adjust(img, trim_rot, brightness=0.76, saturation=0.55, tint=(84, 76, 50), tint_amount=0.24)
    draw = ImageDraw.Draw(img)
    # 5. Chipped teal stripe exposing the plaster.
    stripe_top = room.row(FLOOR_TOP + 8)
    for _ in range(30):
        x = rng.randint(12, W - 20)
        draw.rectangle((x, stripe_top, x + rng.randint(1, 7), stripe_top + rng.choice((1, 3))),
                       fill=(196, 176, 140, 255))
    # 6. Cracked tiles, chipped corners, weeds growing out of the cracks.
    for _ in range(22):
        sx, sy = rng.randint(x0 + 5, x1 - 5), rng.randint(y0 + 5, y1 - 5)
        fx.draw_crack(draw, (sx, sy), rng.uniform(0, 2 * pi), rng.randint(7, 17), rng,
                      (112, 92, 66, 255), (246, 236, 208, 255))
        if rng.random() < 0.6:
            fx.draw_tuft(draw, sx, sy, rng)
    for _ in range(7):
        tx = 10 + 16 * rng.randint(0, (W - 30) // 16)
        ty = y0 + 1 + 16 * rng.randint(0, (y1 - y0) // 16 - 1)
        chip = rng.randint(3, 5)
        draw.polygon([(tx, ty), (tx + chip, ty), (tx, ty + chip)], fill=(150, 132, 100, 255))
    # 7. Puddles where the roof drips (the runtime ambience drips here too).
    for wx, wy in points:
        px, py = room.point(wx, wy)
        draw.ellipse((px - 9, py - 4, px + 9, py + 4), fill=(104, 122, 122, 255))
        draw.ellipse((px - 8, py - 3, px + 8, py + 3), fill=(130, 150, 150, 255))
        draw.ellipse((px - 6, py - 2, px + 2, py + 1), fill=(156, 176, 174, 255))
        draw.line((px - 4, py - 2, px - 2, py - 2), fill=(220, 232, 230, 255))
    # 8. Ivy: dense masses in the corners, single vines between them.
    wall_box = (room.splash_box[0], 0, room.splash_box[2] + 1, room.splash_box[3] + 1)
    for cx, cy, radius, count in ((12, 4, 23, 40), (W - 13, 4, 23, 40),
                                  (W // 2 + 30, 3, 15, 16), (W // 3, 3, 13, 14)):
        fx.draw_ivy(draw, (cx, cy), radius, count, rng, wall_box)
    for x in range(23, W - 20, 33):
        fx.draw_vine(draw, (x + rng.randint(-8, 8), 1), pi / 2, rng.randint(17, 46), rng,
                     leaf_every=4, wobble=0.35, bounds=wall_box)
    floor_box = (x0, y0, x1 + 1, y1 + 1)
    for cx, cy, radius, count in ((13, y0 + 4, 20, 22), (W - 14, y0 + 4, 18, 20),
                                  (13, y1 - 3, 22, 24), (W - 14, y1 - 3, 20, 22)):
        fx.draw_ivy(draw, (cx, cy), radius, count, rng, floor_box)
    side = SIDE_WALL_WIDTH // ART
    for wall_x, box in ((4, (0, 0, side, H)), (W - 5, (W - side, 0, W, H))):
        for _ in range(3):
            fx.draw_vine(draw, (wall_x, rng.randint(H - 20, H - 2)), -pi / 2, rng.randint(45, 130),
                         rng, leaf_every=5, wobble=0.25, bounds=box)
    for _ in range(6):
        fx.draw_vine(draw, (rng.randint(15, W - 15), H - 4), rng.choice((0, pi)), rng.randint(15, 40),
                     rng, leaf_every=5, wobble=0.2, bounds=(side, y1 + 1, W - side, H))
    # 9. Fallen leaves scattered on the floor.
    for _ in range(20):
        fx.draw_leaf(draw, rng.randint(x0 + 3, x1 - 6), rng.randint(y0 + 3, y1 - 3), rng,
                     rng.random() < 0.5, small=True)
    return img


def damage_room(room, points, seed=11):
    rng = random.Random(seed)
    img, size, W, H = room.image, room.image.size, room.W, room.H
    x0, y0, x1, y1 = room.floor_box
    floor = room.mask(room.floor_box)
    # 1. Grime in the grout and scuffed wear paths.
    img = fx.fill(img, (92, 94, 92), fx.mask_and(room.grout, fx.threshold(fx.value_noise(size, 10, seed), 96)))
    wear = fx.mask_and(floor, fx.blocky(fx.threshold(fx.value_noise(size, 35, seed + 1), 186), 2))
    img = fx.multiply(img, (226, 224, 218), wear)
    # 2. Oil stains in stepped tones.
    for _ in range(6):
        soft = fx.soft_blob(size, (rng.randint(x0 + 25, x1 - 25), rng.randint(y0 + 20, y1 - 20)),
                            (rng.randint(15, 30), rng.randint(8, 15)), rng.randrange(99999), cell=6)
        img = fx.multiply(img, (196, 192, 186), fx.mask_and(fx.threshold(soft, 80), floor))
        img = fx.multiply(img, (150, 146, 142), fx.mask_and(fx.threshold(soft, 140), floor))
    # 3. Rust-water stains where the back counters leak onto the floor.
    for _ in range(7):
        cx, cy = rng.randint(x0 + 15, x1 - 15), y0 + rng.randint(2, 11)
        soft = fx.soft_blob(size, (cx, cy), (rng.randint(13, 30), rng.randint(6, 11)),
                            rng.randrange(99999), cell=5)
        img = fx.multiply(img, (232, 204, 172), fx.mask_and(fx.threshold(soft, 70), floor))
        img = fx.multiply(img, (208, 160, 118), fx.mask_and(fx.threshold(soft, 128), floor))
        core = fx.mask_and(fx.threshold(soft, 186), floor)
        img = fx.keep_alpha(Image.alpha_composite(img, fx.rust_colors(size, core, rng.randrange(9999), cell=4, block=1)), img)
    draw = ImageDraw.Draw(img)
    # 4. Missing floor tiles exposing the concrete subfloor.
    for _ in range(7):
        tx = 10 + 16 * rng.randint(0, (W - 30) // 16)
        ty = y0 + 1 + 16 * rng.randint(0, (y1 - y0) // 16 - 1)
        draw.rectangle((tx, ty, tx + 14, ty + 14), fill=(108, 104, 98, 255))
        draw.line((tx, ty, tx + 14, ty), fill=(62, 60, 56, 255))
        draw.line((tx, ty, tx, ty + 14), fill=(74, 72, 68, 255))
        for _ in range(7):
            draw.point((tx + rng.randint(2, 13), ty + rng.randint(2, 13)), fill=(134, 130, 122, 255))
        shard = rng.randint(3, 5)
        draw.polygon([(tx + 14, ty + 14), (tx + 14 - shard, ty + 14), (tx + 14, ty + 14 - shard)],
                     fill=(190, 197, 202, 255))
    # 5. Cracked floor tiles.
    for _ in range(22):
        fx.draw_crack(draw, (rng.randint(x0 + 4, x1 - 4), rng.randint(y0 + 4, y1 - 4)),
                      rng.uniform(0, 2 * pi), rng.randint(6, 14), rng, (66, 70, 76, 255),
                      (228, 232, 234, 255))
    # 6. Wall: missing subway tiles, cracks and rust streaks from the rail.
    sx0, sy0, sx1, sy1 = room.splash_box
    for _ in range(11):
        bx = sx0 + 1 + 14 * rng.randint(0, (sx1 - sx0 - 30) // 14)
        by = sy0 + 7 * rng.randint(0, (sy1 - sy0) // 7 - 1)
        bw = rng.choice((13, 27))
        draw.rectangle((bx, by, bx + bw, by + 6), fill=(132, 128, 120, 255))
        draw.line((bx, by, bx + bw, by), fill=(84, 80, 74, 255))
        for _ in range(4):
            draw.point((bx + rng.randint(1, bw - 1), by + rng.randint(2, 5)), fill=(154, 150, 140, 255))
    for _ in range(12):
        fx.draw_crack(draw, (rng.randint(sx0 + 2, sx1 - 2), rng.randint(sy0 + 2, sy1 - 2)),
                      rng.uniform(0, 2 * pi), rng.randint(4, 10), rng, (112, 118, 126, 255), None)
    for _ in range(18):
        x = rng.randint(sx0 + 2, sx1 - 2)
        length = rng.randint(7, 32)
        for k in range(length):
            color = fx.RUST[2 if k < 2 else 1 if k < length // 2 else 0]
            draw.point((x, sy0 + k), fill=color + (max(60, 235 - k * 6),))
    # 7. Dented kick strip: the highlight breaks around dark pockets.
    stripe_top = room.row(FLOOR_TOP + 8)
    for _ in range(18):
        x = rng.randint(12, W - 20)
        width = rng.randint(2, 6)
        draw.rectangle((x, stripe_top, x + width, stripe_top + 1), fill=(20, 34, 62, 255))
        draw.line((x, stripe_top + 3, x + width, stripe_top + 3), fill=(150, 186, 232, 255))
    # 8. Broken wall panels with dangling wires where the runtime sparks fly.
    for wx, wy in points:
        px, py = room.point(wx, wy)
        draw.rectangle((px - 7, py - 8, px + 7, py + 7), fill=(170, 178, 186, 255))
        draw.rectangle((px - 6, py - 7, px + 6, py + 6), fill=(22, 24, 28, 255))
        for k, color in enumerate(((204, 56, 46), (232, 196, 62), (60, 120, 200))):
            x = px - 3 + k * 3
            for step in range(rng.randint(7, 13)):
                draw.point((x + (step // 3) % 2 * (1 if k % 2 else -1), py - 5 + step), fill=color + (255,))
        draw.polygon([(px + 7, py + 7), (px + 12, py + 9), (px + 8, py + 13), (px + 4, py + 10)],
                     fill=(150, 158, 166, 255), outline=(60, 66, 74, 255))   # fallen cover plate
    # 9. Rust eating the side walls and skirting.
    edges = Image.new("L", size, 0)
    e = ImageDraw.Draw(edges)
    side, bottom = SIDE_WALL_WIDTH // ART, BOTTOM_WALL_HEIGHT // ART
    e.rectangle((0, 0, side - 1, H), fill=255)
    e.rectangle((W - side, 0, W, H), fill=255)
    e.rectangle((0, H - bottom, W, H), fill=255)
    rust = fx.mask_and(edges, fx.threshold(fx.value_noise(size, 9, seed + 6, 2), 172))
    img = fx.keep_alpha(Image.alpha_composite(img, fx.rust_colors(size, rust, seed + 8, cell=5, block=1)), img)
    return img

# --------------------------------------------------------------------------


def build(output=OUTPUT):
    sizes = display_sizes()
    bases = {name: load_base(name, size) for name, size in sizes.items()}
    metal = {name: metalize(name, image) for name, image in bases.items()}
    sets = {
        "warm_clean": bases,
        "warm_overgrown": {name: overgrow(name, image) for name, image in bases.items()},
        "metal_clean": metal,
        "metal_damaged": {name: damage_metal(name, image) for name, image in metal.items()},
    }
    steps = {
        "warm_clean": "source sprite resized to the art grid (LANCZOS, premultiplied alpha)",
        "warm_overgrown": "rot blotches, chipped paint, damp streaks, mould, moss, vines",
        "metal_clean": "HSV wood/paint masks -> luminance steel ramp -> brushed grain",
        "metal_damaged": "metal_clean + grime, edge/seam rust, drips, dents, scratches, broken door",
    }
    days = {MAP_IDS[day.style]: day for day in DAYS}
    manifest = {"tool": "python -m tools.build_kitchens (Pillow)",
                "grid": "1 image pixel = 1 art pixel = 2 world pixels (restaurant/pixel_art.py)",
                "maps": {}}
    for map_id, sprites in sets.items():
        day = days[map_id]
        folder = output / map_id
        folder.mkdir(parents=True, exist_ok=True)
        room = ArtRoom(paint_room(day.style))
        if day.condition == "overgrown":
            image = overgrow_room(room, day.effect_points)
        elif day.condition == "damaged":
            image = damage_room(room, day.effect_points)
        else:
            image = room.image
        # Flatten onto the clean room so translucent strokes never show the window.
        image = Image.alpha_composite(room.image, image).convert("RGB")
        image.save(folder / "room.png", optimize=True)
        files = {"room.png": {"pixels": list(image.size), "world_size": [KITCHEN_WIDTH, KITCHEN_HEIGHT],
                              "source": "painted by tools/build_kitchens.py", "alpha": "opaque"}}
        for name, work in sorted(sprites.items()):
            sprite = finish(work)
            sprite.save(folder / f"{name}.png", optimize=True)
            file, crop = SOURCES[name]
            files[f"{name}.png"] = {"pixels": list(sprite.size), "world_size": list(sizes[name]),
                                    "source": f"assets/kitchen/{file}", "source_crop_ltwh": crop,
                                    "process": steps[map_id], "alpha": "transparent background"}
        manifest["maps"][map_id] = {"day": DAYS.index(day) + 1, "name": day.name,
                                    "style": day.style, "files": files}
        print(f"built {map_id}: {len(files)} files")
    manifest["shared_runtime_art"] = ("Crates, plate, pot and food are loaded from "
                                      "assets/ingredients/sprites in every kitchen.")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build()
