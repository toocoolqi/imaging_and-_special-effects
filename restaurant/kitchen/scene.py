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
        names = {"back_wall", "floor_tile"} | {prop.asset for prop in PROPS}
        self.textures = {name: arcade.load_texture(ASSET_DIR / f"{name}.png")
                         for name in names}
        self.floor = arcade.SpriteList()
        tile_width, tile_height = 141, 66
        for left in range(0, KITCHEN_WIDTH, tile_width):
            for bottom in range(0, FLOOR_TOP + 1, tile_height):
                sprite = arcade.Sprite(self.textures["floor_tile"])
                sprite.width, sprite.height = tile_width, tile_height
                sprite.position = left + tile_width / 2, bottom + tile_height / 2
                self.floor.append(sprite)

    def draw_floor(self):
        self.floor.draw(pixelated=True)
        texture = self.textures["back_wall"]
        height = texture.height * KITCHEN_WIDTH / texture.width
        arcade.draw_texture_rect(texture, arcade.LBWH(
            0, KITCHEN_HEIGHT - height, KITCHEN_WIDTH, height), pixelated=True)
        # Extend the original warm wood border around the larger floor.
        for left, bottom, width, height in (
            (0, 0, SIDE_WALL_WIDTH, FLOOR_TOP),
            (KITCHEN_WIDTH - SIDE_WALL_WIDTH, 0, SIDE_WALL_WIDTH, FLOOR_TOP),
            (0, 0, KITCHEN_WIDTH, BOTTOM_WALL_HEIGHT),
        ):
            arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, (92, 57, 47))
        for x in (SIDE_WALL_WIDTH - 7, KITCHEN_WIDTH - SIDE_WALL_WIDTH + 1):
            arcade.draw_lbwh_rectangle_filled(x, BOTTOM_WALL_HEIGHT, 6,
                                              FLOOR_TOP - BOTTOM_WALL_HEIGHT,
                                              (181, 121, 77))
        arcade.draw_lbwh_rectangle_filled(SIDE_WALL_WIDTH - 1, BOTTOM_WALL_HEIGHT - 6,
                                          KITCHEN_WIDTH - 2 * SIDE_WALL_WIDTH + 2,
                                          6, (181, 121, 77))

    def draw_props(self):
        # Tables first, their decorations second. Solid full bounds mean the
        # chef never needs to be hidden behind a table's front/legs.
        for prop in PROPS:
            arcade.draw_texture_rect(self.textures[prop.asset],
                                     arcade.XYWH(*prop.rectangle), pixelated=True)
