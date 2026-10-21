"""Draw prepared pictures from the supplied sheets with Arcade only."""
from pathlib import Path

import arcade

from restaurant.kitchen.layout import (
    BOTTOM_WALL_HEIGHT, FLOOR_TOP, KITCHEN_HEIGHT, KITCHEN_WIDTH,
    PROPS, SIDE_WALL_WIDTH,
)

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "kitchen"


class KitchenScene:
    def __init__(self):
        names = {"floor_tile"} | {prop.asset for prop in PROPS}
        self.textures = {name: arcade.load_texture(ASSET_DIR / f"{name}.png")
                         for name in names}
        self.floor = arcade.SpriteList()
        tile_width, tile_height = 128, 64
        for left in range(0, KITCHEN_WIDTH, tile_width):
            for bottom in range(0, KITCHEN_HEIGHT, tile_height):
                sprite = arcade.Sprite(self.textures["floor_tile"])
                sprite.width, sprite.height = tile_width, tile_height
                sprite.position = left + tile_width / 2, bottom + tile_height / 2
                self.floor.append(sprite)

    def draw_floor(self):
        self.floor.draw(pixelated=True)
        # One viewpoint and tile scale across the whole room. No perspective
        # back-wall photograph is layered over the top of this floor.
        for left, bottom, width, height in (
            (0, 0, SIDE_WALL_WIDTH, KITCHEN_HEIGHT),
            (KITCHEN_WIDTH - SIDE_WALL_WIDTH, 0, SIDE_WALL_WIDTH, KITCHEN_HEIGHT),
            (0, 0, KITCHEN_WIDTH, BOTTOM_WALL_HEIGHT),
            (0, FLOOR_TOP, KITCHEN_WIDTH, KITCHEN_HEIGHT - FLOOR_TOP),
        ):
            arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, (92, 57, 47))
        for x in (SIDE_WALL_WIDTH - 7, KITCHEN_WIDTH - SIDE_WALL_WIDTH + 1):
            arcade.draw_lbwh_rectangle_filled(x, BOTTOM_WALL_HEIGHT, 6,
                                              FLOOR_TOP - BOTTOM_WALL_HEIGHT,
                                              (181, 121, 77))
        for y in (BOTTOM_WALL_HEIGHT - 6, FLOOR_TOP):
            arcade.draw_lbwh_rectangle_filled(SIDE_WALL_WIDTH - 1, y,
                                              KITCHEN_WIDTH - 2 * SIDE_WALL_WIDTH + 2,
                                              6, (181, 121, 77))

    def draw_props(self):
        # Tables first, their decorations second. Solid full bounds mean the
        # chef never needs to be hidden behind a table's front/legs.
        for prop in PROPS:
            arcade.draw_texture_rect(self.textures[prop.asset],
                                     arcade.XYWH(*prop.rectangle), pixelated=True)
