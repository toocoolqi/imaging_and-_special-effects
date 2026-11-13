"""Crisp architectural trim and flooring, batched once using Arcade shapes."""
from arcade.shape_list import ShapeElementList, create_rectangle_filled

from restaurant.kitchen.layout import FLOOR_TOP, KITCHEN_HEIGHT, KITCHEN_WIDTH

INK = (65, 49, 43)
WOOD = (174, 111, 70)
LIGHT_WOOD = (210, 156, 99)
CREAM = (238, 220, 181)
TEAL = (92, 139, 126)
DARK_TEAL = (54, 88, 79)


class PixelDetails:
    def __init__(self):
        self.shapes = ShapeElementList()

    def rect(self, x, y, w, h, color):
        self.shapes.append(create_rectangle_filled(x + w / 2, y + h / 2, w, h, color))

    def frame(self, x, y, w, h, color, edge=INK, thickness=2):
        self.rect(x, y, w, h, edge)
        self.rect(x + thickness, y + thickness, w - thickness * 2, h - thickness * 2, color)

    def draw(self):
        self.shapes.draw()


def room_details(style="warm"):
    metal = style.startswith("metal")
    worn = style in ("overgrown", "metal_damaged")
    floor = ((154, 167, 176), (174, 187, 195)) if metal else ((224, 207, 168), (231, 214, 177))
    if style == "overgrown":
        floor = ((162, 172, 117), (178, 182, 125))
    trim = (118, 132, 146) if metal else WOOD
    light = (206, 218, 226) if metal else LIGHT_WOOD
    wall = (189, 202, 211) if metal else CREAM
    art = PixelDetails()
    r, f = art.rect, art.frame
    # Quiet cream tiles, occasional terracotta/sage motifs. No enlarged JPEG.
    r(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT, INK)
    r(18, 18, KITCHEN_WIDTH - 36, FLOOR_TOP - 18, (173, 156, 124))
    for y in range(20, FLOOR_TOP - 2, 32):
        for x in range(20, KITCHEN_WIDTH - 20, 32):
            shade = floor[(x // 32 + y // 32) % 2]
            width, height = min(30, KITCHEN_WIDTH - 20 - x), min(30, FLOOR_TOP - 2 - y)
            r(x, y, width, height, shade)
            r(x, y + height - 2, width, 2, (209, 218, 222) if metal else (239, 223, 190))
            if x % 128 == 20 and y % 128 == 20 and height >= 24:
                color = (154, 174, 145) if (x + y) % 256 == 40 else (197, 148, 108)
                r(x + 12, y + 6, 6, 18, color)
                r(x + 6, y + 12, 18, 6, color)
                r(x + 12, y + 12, 6, 6, shade)
    # Straight wall caps and a tiled backsplash in the same viewpoint.
    for x in (0, KITCHEN_WIDTH - 18):
        r(x, 0, 18, KITCHEN_HEIGHT, (104, 70, 52))
        r(x + 4, 18, 10, KITCHEN_HEIGHT - 24, light)
    r(18, 0, KITCHEN_WIDTH - 36, 18, trim)
    r(18, 14, KITCHEN_WIDTH - 36, 4, light)
    r(18, FLOOR_TOP, KITCHEN_WIDTH - 36, KITCHEN_HEIGHT - FLOOR_TOP - 12, wall)
    for y in range(FLOOR_TOP + 8, 692, 28):
        r(18, y, KITCHEN_WIDTH - 36, 2, (212, 189, 151))
        for x in range(20 + (14 if y % 56 else 0), KITCHEN_WIDTH - 20, 40):
            r(x, y, 2, min(28, 692 - y), (212, 189, 151))
    r(18, FLOOR_TOP, KITCHEN_WIDTH - 36, 5, DARK_TEAL)
    r(18, FLOOR_TOP + 5, KITCHEN_WIDTH - 36, 3, TEAL)
    r(18, 692, KITCHEN_WIDTH - 36, 12, trim)
    r(18, 692, KITCHEN_WIDTH - 36, 4, LIGHT_WOOD)
    # A clock and small wall chalkboard; all decoration has a useful location.
    f(894, 649, 30, 30, CREAM, thickness=4)
    r(908, 663, 2, 9, INK)
    r(908, 661, 8, 2, INK)
    f(522, 625, 60, 56, DARK_TEAL, edge=WOOD, thickness=4)
    for y, length in ((666, 35), (657, 40), (648, 30), (639, 36)):
        r(532, y, length, 2, (189, 207, 173))
    # Pantry plinth is flat floor trim, not an extra obstacle.
    f(50, 38, 370, 18, WOOD, edge=(123, 87, 59))
    for x in (64, 154, 244, 334):
        r(x, 44, 52, 5, LIGHT_WOOD)
    # Dish, cooker and service mats stay flat underfoot.
    for x, y, w in ((48, 436, 166), (273, 431, 118), (638, 434, 212)):
        f(x, y, w, 24, (110, 126, 105), edge=(89, 105, 86))
        for stripe in range(x + 6, x + w - 4, 8):
            r(stripe, y + 4, 2, 16, (139, 151, 124))
    if worn:
        for x, y in ((58, 214), (423, 505), (553, 102), (827, 278), (751, 574)):
            for step in range(5):
                r(x + step * 5, y + (step % 3) * 3, 6, 2, (93, 79, 67))
        for x in (38, 230, 486, 608, 921):
            if style == "overgrown":
                for i in range(8):
                    y = 680 - i * 8
                    r(x + i % 3, y, 3, 10, (55, 90, 47))
                    r(x - 8 if i % 2 else x + 3, y, 10, 5, (86, 124, 60))
            else:
                for i in range(4):
                    r(x + i * 4, 611 + i * 4, 13, 4, (141, 81, 58))
    return art
