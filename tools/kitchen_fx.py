"""Image-processing building blocks for the kitchen variants (Pillow only).

Each function takes and returns PIL images so the steps can be explained and
tested one at a time. Techniques used (module tutorials in brackets):

- HSV colour-space masks to find wood / painted / dark pixels  [Week 11]
- Luminance remapping (recolouring) to turn wood into steel     [Weeks 4, 7]
- Value noise (random grid + bicubic upscale) for organic masks [Weeks 9, 11]
- Morphology (Min/Max filters) for edge bands and dilation       [Week 7]
- Multiply / screen blending for stains, grime and dents         [Week 8]
- Procedural pixel-art drawing (vines, cracks, rust drips)       [Weeks 3, 4]

Procedural detail is drawn on a small canvas whose pixels are the game's art
pixels and enlarged with NEAREST filtering, so every decoration lands on the
same chunky pixel grid as the rest of the pixel-art game.
"""
from math import cos, pi, sin
import random

from PIL import Image, ImageChops, ImageFilter

# --------------------------------------------------------------------------
# Masks and noise
# --------------------------------------------------------------------------


def value_noise(size, cell, seed, octaves=2):
    """Smooth random field 0-255: a coarse random grid enlarged bicubically."""
    rng = random.Random(seed)
    w, h = size
    result = None
    weight_total = 0.0
    for octave in range(octaves):
        c = max(2, cell // (2 ** octave))
        gw, gh = w // c + 3, h // c + 3
        grid = Image.new("L", (gw, gh))
        grid.putdata([rng.randrange(256) for _ in range(gw * gh)])
        layer = grid.resize((gw * c, gh * c), Image.BICUBIC).crop((c, c, c + w, c + h))
        weight = 1.0 / (octave + 1)
        if result is None:
            result = layer
        else:
            result = Image.blend(result, layer, weight / (weight_total + weight))
        weight_total += weight
    return result


def threshold(gray, low, high=None):
    """Hard (high=None) or soft ramp threshold of an L image."""
    if high is None:
        return gray.point(lambda v: 255 if v >= low else 0)
    span = max(1, high - low)
    return gray.point(lambda v: 0 if v <= low else 255 if v >= high else int((v - low) * 255 / span))


def mask_and(*masks):
    out = masks[0]
    for mask in masks[1:]:
        out = ImageChops.multiply(out, mask)
    return out


def mask_or(*masks):
    out = masks[0]
    for mask in masks[1:]:
        out = ImageChops.lighter(out, mask)
    return out


def scale_mask(mask, factor):
    return mask.point(lambda v: int(min(255, v * factor)))


def solid_alpha(image, cutoff=128):
    return threshold(image.getchannel("A"), cutoff)


def hsv_mask(image, hues, min_s=0, max_s=255, min_v=0, max_v=255):
    """Pixels whose hue (degrees) lies in any (start, end) range and S/V limits."""
    h, s, v = image.convert("RGB").convert("HSV").split()

    def in_hue(value):
        degrees = value * 360 / 255
        return 255 if any(a <= degrees <= b for a, b in hues) else 0

    return mask_and(h.point(in_hue),
                    s.point(lambda x: 255 if min_s <= x <= max_s else 0),
                    v.point(lambda x: 255 if min_v <= x <= max_v else 0))


def wood_mask(image):
    return mask_and(hsv_mask(image, ((0, 42), (340, 360)), min_s=70, min_v=60), solid_alpha(image))


def paint_mask(image):
    """The teal painted cabinet fronts of the warm kitchen."""
    return mask_and(hsv_mask(image, ((135, 200),), min_s=35, min_v=50), solid_alpha(image))


def outline_mask(image):
    return mask_and(hsv_mask(image, ((0, 360),), max_v=62), solid_alpha(image))


def erode(mask, radius):
    return mask.filter(ImageFilter.MinFilter(radius * 2 + 1)) if radius else mask


def dilate(mask, radius):
    return mask.filter(ImageFilter.MaxFilter(radius * 2 + 1)) if radius else mask


def edge_band(image, width):
    """Opaque pixels within `width` pixels of the sprite silhouette."""
    alpha = solid_alpha(image)
    return ImageChops.subtract(alpha, erode(alpha, width))


def vertical_bias(size, top=0.0, bottom=1.0):
    """L gradient: value `top` at the top row to `bottom` at the bottom row."""
    w, h = size
    column = Image.new("L", (1, h))
    column.putdata([int(255 * (top + (bottom - top) * y / max(1, h - 1))) for y in range(h)])
    return column.resize((w, h))


def resize_rgba(image, size, method):
    """Resize with premultiplied alpha so transparent pixels never leave a
    dark fringe on the edges."""
    return image.convert("RGBa").resize(size, method).convert("RGBA")


def blocky(mask, factor):
    """Quantise a mask to factor-sized pixels (pixel-art chunks)."""
    w, h = mask.size
    small = mask.resize((max(1, w // factor), max(1, h // factor)), Image.BOX)
    return small.resize((w, h), Image.NEAREST)


# --------------------------------------------------------------------------
# Colour operations (all respect the original alpha channel)
# --------------------------------------------------------------------------


def keep_alpha(result, original):
    result = result.convert("RGBA")
    result.putalpha(original.getchannel("A"))
    return result


def fill(image, color, mask):
    """Paint a flat colour through a mask (0-255 is coverage)."""
    layer = Image.new("RGBA", image.size, tuple(color) + (255,))
    return keep_alpha(Image.composite(layer, image, mask), image)


def multiply(image, color, mask):
    layer = ImageChops.multiply(image.convert("RGB"), Image.new("RGB", image.size, color))
    return keep_alpha(Image.composite(layer.convert("RGBA"), image, mask), image)


def screen(image, color, mask):
    layer = ImageChops.screen(image.convert("RGB"), Image.new("RGB", image.size, color))
    return keep_alpha(Image.composite(layer.convert("RGBA"), image, mask), image)


def ramp_recolor(image, dark, light, mask, lo=0, hi=255):
    """Replace hue by a two-colour ramp driven by each pixel's luminance.

    This is how the warm wood becomes steel: bright wood -> bright steel,
    shadowed wood -> shadowed steel, so the original shading is preserved.
    Luminance lo..hi is stretched onto the dark..light ramp.
    """
    luma = image.convert("L")

    def channel(a, b):
        def f(v):
            t = min(1.0, max(0.0, (v - lo) / max(1, hi - lo)))
            return int(a + (b - a) * t)
        return luma.point(f)

    rgb = Image.merge("RGB", [channel(dark[i], light[i]) for i in range(3)])
    return keep_alpha(Image.composite(rgb.convert("RGBA"), image, mask), image)


def adjust(image, mask, brightness=1.0, saturation=1.0, tint=None, tint_amount=0.0):
    """Darken/desaturate/tint only where mask is set."""
    rgb = image.convert("RGB")
    gray = rgb.convert("L").convert("RGB")
    out = Image.blend(gray, rgb, saturation) if saturation != 1.0 else rgb
    if brightness != 1.0:
        out = out.point(lambda v: int(min(255, v * brightness)))
    if tint is not None and tint_amount:
        out = Image.blend(out, Image.new("RGB", image.size, tint), tint_amount)
    return keep_alpha(Image.composite(out.convert("RGBA"), image, mask), image)


def brushed_streaks(image, mask, seed, strength=14, scale=2):
    """Horizontal brushed-metal grain: random rows stretched along x."""
    w, h = image.size
    rng = random.Random(seed)
    rows = Image.new("L", (max(2, w // 48), max(1, h // scale)))
    rows.putdata([rng.randrange(256) for _ in range(rows.width * rows.height)])
    grain = rows.resize((w, max(1, h // scale)), Image.BILINEAR).resize((w, h), Image.NEAREST)
    light = mask_and(threshold(grain, 160, 230), mask)
    dark = mask_and(threshold(grain.point(lambda v: 255 - v), 170, 240), mask)
    image = screen(image, (strength * 3,) * 3, scale_mask(light, 0.55))
    return multiply(image, (255 - strength * 2,) * 3, scale_mask(dark, 0.6))


# --------------------------------------------------------------------------
# Procedural pixel-art layers (drawn at 1x, enlarged by NEAREST)
# --------------------------------------------------------------------------

LEAF_DARK, LEAF_MID, LEAF_LIGHT, STEM = (46, 86, 44), (78, 128, 58), (128, 170, 74), (66, 74, 40)


def pixel_layer(size, factor):
    """Transparent drawing canvas at 1/factor resolution."""
    w, h = size
    return Image.new("RGBA", (max(1, w // factor), max(1, h // factor)), (0, 0, 0, 0))


def enlarge(layer, size):
    return layer.resize(size, Image.NEAREST)


# (dx, dy, tone) for a leaf pointing right; tone 0 dark, 1 mid, 2 light.
_LEAF = ((1, -1, 1), (2, -1, 2), (3, -1, 1),
         (0, 0, 1), (1, 0, 2), (2, 0, 1), (3, 0, 1), (4, 0, 0),
         (1, 1, 1), (2, 1, 1), (3, 1, 0))
_SMALL_LEAF = ((0, 0, 1), (1, 0, 2), (2, 0, 1), (1, -1, 1), (2, 1, 0))


def draw_leaf(draw, x, y, rng, flip=False, small=False):
    """A pixel-art leaf with a dark underside and a light highlight."""
    tones = (LEAF_DARK, LEAF_MID, LEAF_LIGHT)
    d = -1 if flip else 1
    x, y = int(x), int(y)
    for dx, dy, tone in (_SMALL_LEAF if small else _LEAF):
        draw.point((x + dx * d, y + dy), fill=tones[tone])


def draw_ivy(draw, center, radius, count, rng, bounds):
    """A dense mass of overlapping leaves, thicker towards its centre."""
    cx, cy = center
    for _ in range(count):
        r = radius * rng.random() ** 1.6
        a = rng.uniform(0, 2 * pi)
        x, y = cx + r * cos(a), cy + r * sin(a) * 0.7
        if bounds[0] + 2 <= x < bounds[2] - 5 and bounds[1] + 2 <= y < bounds[3] - 2:
            draw_leaf(draw, x, y, rng, rng.random() < 0.5)


def draw_vine(draw, start, heading, length, rng, leaf_every=3, wobble=0.45, bounds=None):
    """Random-walk stem with alternating leaves. heading in radians (y down)."""
    x, y = start
    angle = heading
    flip = False
    for step in range(length):
        angle += rng.uniform(-wobble, wobble)
        angle = heading + max(-0.9, min(0.9, angle - heading))
        nx, ny = x + cos(angle), y + sin(angle)
        if bounds and not (bounds[0] <= nx < bounds[2] and bounds[1] <= ny < bounds[3]):
            break
        draw.point((int(nx), int(ny)), fill=STEM)
        x, y = nx, ny
        if step % leaf_every == 0 and step:
            draw_leaf(draw, x + (1 if flip else -1), y, rng, flip)
            flip = not flip
    return x, y


def draw_crack(draw, start, heading, length, rng, dark, light, branch=0.25):
    """Jagged crack line with a light lip under it; occasionally branches."""
    x, y = start
    angle = heading
    for step in range(length):
        angle += rng.uniform(-0.7, 0.7)
        x, y = x + cos(angle), y + sin(angle)
        draw.point((int(x), int(y)), fill=dark)
        if light is not None:
            draw.point((int(x), int(y) + 1), fill=light)
        if step > 3 and rng.random() < branch / length * 4:
            draw_crack(draw, (x, y), angle + rng.choice((-1, 1)) * rng.uniform(0.6, 1.2),
                       max(2, length // 3), rng, dark, light, branch / 2)


def draw_tuft(draw, x, y, rng):
    """Tiny weed/grass tuft growing from a crack."""
    x, y = int(x), int(y)
    for dx, height in ((-1, rng.randint(1, 2)), (0, rng.randint(2, 4)), (1, rng.randint(1, 3))):
        for k in range(height):
            draw.point((x + dx, y - k), fill=LEAF_LIGHT if k == height - 1 else LEAF_MID)
    draw.point((x, y + 1), fill=LEAF_DARK)


RUST = ((82, 42, 26), (116, 58, 30), (148, 78, 38), (176, 106, 56))


def rust_colors(size, mask, seed, cell=10, block=2):
    """Colour a rust mask with a 4-tone ramp chosen by chunky noise."""
    w, h = size
    small = (max(1, w // block), max(1, h // block))
    n = value_noise(small, max(2, cell // block), seed, octaves=2).resize(size, Image.NEAREST)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    bands = ((0, 96), (96, 136), (136, 180), (180, 256))
    for color, (lo, hi) in zip(RUST, bands):
        band = n.point(lambda v, lo=lo, hi=hi: 255 if lo <= v < hi else 0)
        layer = Image.composite(Image.new("RGBA", size, color + (255,)), layer, mask_and(band, mask))
    return layer


def soft_blob(size, center, radii, seed, cell=16):
    """Organic stain mask: a radial falloff broken up by smooth noise (0-255)."""
    cx, cy = int(center[0]), int(center[1])
    rx, ry = int(radii[0]), int(radii[1])
    falloff = ImageChops.invert(Image.radial_gradient("L")).resize((rx * 2, ry * 2))
    mask = Image.new("L", size, 0)
    mask.paste(falloff, (cx - rx, cy - ry))
    noise = value_noise(size, cell, seed, 2).point(lambda v: int(120 + v * 135 / 255))
    return ImageChops.multiply(mask, noise)


def dent(draw_dark, draw_light, cx, cy, rx, ry):
    """A concave dent lit from the top-left.

    The upper-left inner rim falls into shadow and the lower-right rim catches
    the light, which is what makes a flat patch read as pushed-in metal.
    """
    box = (cx - rx, cy - ry, cx + rx, cy + ry)
    draw_dark.ellipse(box, fill=(0, 0, 0, 52))
    draw_dark.arc(box, 170, 320, fill=(0, 0, 0, 150), width=2)   # left -> top
    draw_light.arc(box, 10, 120, fill=(255, 255, 255, 130), width=1)  # right -> bottom
