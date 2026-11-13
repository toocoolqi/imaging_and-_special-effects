"""Arcade-only room renderer with floor-based overlap ordering."""
from math import sin
from pathlib import Path

import arcade

from restaurant.kitchen.details import room_details
from restaurant.kitchen.layout import PROPS, WALL_ART

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "kitchen"
FOOD_DIR = ASSET_DIR.parent / "ingredients" / "sprites"
TASK2_ASSETS = {
    "crate_sandwich": "box_sandwich", "crate_tomato": "box_tomato",
    "crate_noodles": "box_noodles", "crate_milk": "box_milk",
    "plate": "plate", "pot": "pot_empty",
}

# Top-left image pixels. Arcade extracts these six transparent sprite regions
# at load time; the original atlas is preserved and no extra image tool is used.
ATLAS_REGIONS = {
    "sink": (124, 58, 578, 271),
    "pass_counter": (803, 108, 634, 222),
    "spice_shelf": (178, 395, 501, 250),
    "extractor": (841, 371, 550, 277),
    "clean_board": (199, 738, 440, 197),
    "service_hatch": (816, 686, 612, 267),
}


def load_textures(props=PROPS):
    names = {prop.asset for prop in props} | {item[0] for item in WALL_ART}
    textures = {name: arcade.load_texture(
                    FOOD_DIR / f"{TASK2_ASSETS[name]}.png" if name in TASK2_ASSETS
                    else ASSET_DIR / f"{name}.png")
                for name in names - ATLAS_REGIONS.keys()}
    textures.update({name: arcade.load_texture(FOOD_DIR / f"{name}.png")
                     for name in ("sandwich", "tomato", "noodles", "milk")})
    atlas = arcade.load_texture(ASSET_DIR / "restaurant_details.png")
    textures.update({name: atlas.crop(*region) for name, region in ATLAS_REGIONS.items()})
    textures.update({name: arcade.load_texture(FOOD_DIR / f"{name}.png")
                     for name in ("pot_cooking", "pot_cooked")})
    textures["creamy_noodles"] = textures["noodles"]
    return textures


class KitchenScene:
    def __init__(self, day=None):
        props = PROPS if day is None else day.props
        self.style = "warm" if day is None else day.style
        self.textures = load_textures(props)
        self.floor = room_details(self.style)
        self.props = {prop.prop_id: prop for prop in props if prop.solid}
        self.decorations = {prop_id: tuple(child for child in props if child.support == prop_id)
                            for prop_id in self.props}

    def draw_floor(self):
        self.floor.draw()
        for asset, x, y, width, height in WALL_ART:
            arcade.draw_texture_rect(self.textures[asset], arcade.XYWH(x, y, width, height),
                                     pixelated=False)

    def draw_order(self, foot_y):
        """Back to front, with tabletop decorations attached to their table."""
        entries = [(prop.depth_y, prop.prop_id) for prop in self.props.values()]
        entries.append((foot_y, "player"))
        return [prop_id for _, prop_id in sorted(entries, reverse=True)]

    def draw_prop(self, prop, asset=None):
        # Source crops are larger than their displayed size. Linear minification
        # avoids jagged JPEG edge samples when reducing the supplied pictures.
        arcade.draw_texture_rect(self.textures[asset or prop.asset],
                                 arcade.XYWH(*prop.rectangle), pixelated=False)

    def draw_plate_food(self, items, x, y, size):
        for index, ingredient in enumerate(items):
            texture = self.textures[ingredient]
            scale = size / max(texture.width, texture.height)
            arcade.draw_texture_rect(texture, arcade.XYWH(
                x - size * .6 + (index % 2) * size * 1.2,
                y + size * .3 - (index // 2) * size * .65,
                texture.width * scale, texture.height * scale), pixelated=False)

    def draw_props(self, player, players, state=None, pot=None):
        for prop_id in self.draw_order(player.ground_position[1]):
            if prop_id == "player":
                players.draw(pixelated=True)
                if state is not None and state.carrying_plate:
                    x, y = player.position
                    arcade.draw_texture_rect(self.textures["plate"],
                                             arcade.XYWH(x + 30, y, 42, 29), pixelated=False)
                    self.draw_plate_food(state.plate.ingredients, x + 30, y, 13)
                if state is not None and state.held:
                    texture = self.textures[state.held]
                    size = 24
                    scale = size / max(texture.width, texture.height)
                    arcade.draw_texture_rect(texture,
                        arcade.XYWH(player.position[0] + 31, player.position[1] + 5,
                                    texture.width * scale, texture.height * scale), pixelated=False)
                continue
            prop = self.props[prop_id]
            self.draw_prop(prop)
            for decoration in self.decorations[prop_id]:
                if decoration.prop_id == "display_plate" and state is not None:
                    if not state.carrying_plate:
                        self.draw_prop(decoration)
                        self.draw_plate_food(state.plate.ingredients, decoration.x, decoration.y, 22)
                elif decoration.prop_id == "display_pot" and pot is not None:
                    texture = {"cooking": "pot_cooking", "ready": "pot_cooked"}.get(pot.state)
                    self.draw_prop(decoration, texture)
                    if pot.state == "cooking":
                        for index in range(4):
                            phase = (pot.elapsed * 2 + index / 4) % 1
                            arcade.draw_circle_outline(
                                decoration.x - 12 + index * 8 + 2 * sin(phase * 6),
                                decoration.y + 8 + phase * 20, 1 + phase * 2,
                                (219, 246, 252, int(220 * (1 - phase))), 1)
                else:
                    self.draw_prop(decoration)
