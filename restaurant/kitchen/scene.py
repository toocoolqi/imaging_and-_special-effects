"""Arcade-only room renderer with floor-based overlap ordering."""
from pathlib import Path

import arcade

from restaurant.kitchen.details import room_details
from restaurant.kitchen.layout import PROPS, SOLID_PROPS, WALL_ART
from restaurant.ingredients.models import POT_RECIPE
from restaurant.shared.contracts import PlateLocation, PotStage

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


def load_textures():
    names = {prop.asset for prop in PROPS} | {item[0] for item in WALL_ART}
    textures = {name: arcade.load_texture(
                    FOOD_DIR / f"{TASK2_ASSETS[name]}.png" if name in TASK2_ASSETS
                    else ASSET_DIR / f"{name}.png")
                for name in names - ATLAS_REGIONS.keys()}
    textures.update({name: arcade.load_texture(FOOD_DIR / f"{name}.png")
                     for name in ("sandwich", "tomato", "noodles", "milk", "pot_cooking", "pot_cooked")})
    textures[POT_RECIPE.dish] = arcade.load_texture(FOOD_DIR / f"{POT_RECIPE.dish}.png")
    atlas = arcade.load_texture(ASSET_DIR / "restaurant_details.png")
    textures.update({name: atlas.crop(*region) for name, region in ATLAS_REGIONS.items()})
    return textures


def draw_icon(texture, x, y, size):
    scale = size / max(texture.width, texture.height)
    arcade.draw_texture_rect(texture, arcade.XYWH(x, y, texture.width * scale,
                                                  texture.height * scale), pixelated=False)


class KitchenScene:
    def __init__(self):
        self.textures = load_textures()
        self.floor = room_details()
        self.props = {prop.prop_id: prop for prop in PROPS}
        self.decorations = {prop.prop_id: tuple(child for child in PROPS
                            if child.support == prop.prop_id) for prop in SOLID_PROPS}

    def draw_floor(self):
        self.floor.draw()
        for asset, x, y, width, height in WALL_ART:
            arcade.draw_texture_rect(self.textures[asset], arcade.XYWH(x, y, width, height),
                                     pixelated=False)

    def draw_order(self, foot_y):
        """Back to front, with tabletop decorations attached to their table."""
        entries = [(prop.depth_y, prop.prop_id) for prop in SOLID_PROPS]
        entries.append((foot_y, "player"))
        return [prop_id for _, prop_id in sorted(entries, reverse=True)]

    def draw_prop(self, prop, asset=None):
        # Source crops are larger than their displayed size. Linear minification
        # avoids jagged JPEG edge samples when reducing the supplied pictures.
        arcade.draw_texture_rect(self.textures[asset or prop.asset],
                                 arcade.XYWH(*prop.rectangle), pixelated=False)

    def draw_plate_contents(self, ingredients, x, y, size):
        if POT_RECIPE.dish in ingredients:
            draw_icon(self.textures[POT_RECIPE.dish], x, y, size * 2.3)
            return
        for index, ingredient in enumerate(ingredients):
            draw_icon(self.textures[ingredient], x + (-0.6 + index % 2 * 1.2) * size,
                      y + (0.32 - index // 2 * 0.64) * size, size)

    def draw_pot(self, prop, pot):
        asset = {PotStage.COOKING: "pot_cooking", PotStage.READY: "pot_cooked"}.get(pot.stage)
        self.draw_prop(prop, asset)
        if pot.stage is PotStage.COOKING:
            elapsed = POT_RECIPE.duration - pot.remaining_seconds
            for index in range(5):
                phase = (elapsed * 1.7 + index / 5) % 1
                arcade.draw_circle_outline(prop.x - 12 + index * 6, prop.y + 9 + phase * 23,
                                           1.5 + phase * 2, (221, 246, 239, int(220 * (1 - phase))), 1)
        elif pot.stage is PotStage.LOADING:
            draw_icon(self.textures[pot.ingredients[0]], prop.x, prop.y + 5, 13)

    def draw_props(self, player, players, state=None):
        for prop_id in self.draw_order(player.ground_position[1]):
            if prop_id == "player":
                players.draw(pixelated=True)
                if state is not None:
                    x, y = player.position
                    x += -31 if player.direction == "left" else 31
                    y += 5
                    if state.plate.location is PlateLocation.CARRIED:
                        draw_icon(self.textures["plate"], x, y, 43)
                        self.draw_plate_contents(state.plate.ingredients, x, y, 13)
                    elif state.held:
                        draw_icon(self.textures[state.held], x, y, 24)
                continue
            prop = self.props[prop_id]
            self.draw_prop(prop)
            for decoration in self.decorations[prop_id]:
                if decoration.prop_id == "display_plate" and state is not None:
                    if state.plate.location is PlateLocation.DOCKED:
                        self.draw_prop(decoration)
                        self.draw_plate_contents(state.plate.ingredients, decoration.x, decoration.y, 22)
                elif decoration.prop_id == "display_pot" and state is not None:
                    self.draw_pot(decoration, state.pot)
                else:
                    self.draw_prop(decoration)
