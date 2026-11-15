"""Arcade-only room renderer with floor-based overlap ordering."""
from math import sin
from pathlib import Path

import arcade

from restaurant.ingredients.models import POT_RECIPE
from restaurant.kitchen.details import room_details
from restaurant.kitchen.layout import KITCHEN_HEIGHT, KITCHEN_WIDTH, PROPS, WALL_ART
from restaurant.pixel_art import draw_pixel_texture
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


def load_textures(props=PROPS, art_dir=None):
    """Food and cookware come from Member 2's sprites in every kitchen.

    Furniture and wall art come from the day's prepared set in art_dir
    (assets/kitchen/<map_id>/, built by tools/build_kitchens.py). Without a
    set, the original warm pictures are used, as the menu does.
    """
    names = {prop.asset for prop in props} | {item[0] for item in WALL_ART}
    prepared = {name for name in names - TASK2_ASSETS.keys()
                if art_dir is not None and (art_dir / f"{name}.png").is_file()}
    textures = {name: arcade.load_texture(
                    FOOD_DIR / f"{TASK2_ASSETS[name]}.png" if name in TASK2_ASSETS
                    else art_dir / f"{name}.png" if name in prepared
                    else ASSET_DIR / f"{name}.png")
                for name in names - (ATLAS_REGIONS.keys() - prepared)}
    textures.update({name: arcade.load_texture(FOOD_DIR / f"{name}.png")
                     for name in ("sandwich", "tomato", "noodles", "milk")})
    missing = ATLAS_REGIONS.keys() - prepared
    if missing:
        atlas = arcade.load_texture(ASSET_DIR / "restaurant_details.png")
        textures.update({name: atlas.crop(*ATLAS_REGIONS[name]) for name in missing})
    textures.update({name: arcade.load_texture(FOOD_DIR / f"{name}.png")
                     for name in ("pot_cooking", "pot_cooked")})
    textures[POT_RECIPE.dish] = arcade.load_texture(FOOD_DIR / f"{POT_RECIPE.dish}.png")
    return textures


def draw_icon(texture, x, y, size):
    scale = size / max(texture.width, texture.height)
    draw_pixel_texture(texture, arcade.XYWH(x, y, texture.width * scale,
                                            texture.height * scale))


def draw_tomato_pieces(x, y, size):
    """A small pixel cluster that reads as diced tomato at both icon sizes."""
    unit = size / 15
    for dx, dy, edge in ((-7, -4, 4), (-3, -5, 4), (1, -3, 5), (-5, 1, 4),
                         (-1, 2, 5), (4, 1, 3)):
        px, py = x + dx * unit, y + dy * unit
        arcade.draw_lbwh_rectangle_filled(px, py, edge * unit, edge * unit, (124, 40, 29))
        arcade.draw_lbwh_rectangle_filled(px + unit, py + unit, (edge - 1) * unit,
                                          (edge - 1) * unit, (222, 74, 48))
        arcade.draw_lbwh_rectangle_filled(px + unit, py + (edge - 1) * unit,
                                          (edge - 2) * unit, unit, (251, 135, 87))


class KitchenScene:
    def __init__(self, day=None):
        props = PROPS if day is None else day.props
        self.style = "warm" if day is None else day.style
        art_dir = None if day is None else day.art_dir
        self.textures = load_textures(props, art_dir)
        room = None if art_dir is None else art_dir / "room.png"
        # The prepared room is stored on the art grid and drawn 1:1. Without
        # it, the original Arcade-shape floor is used.
        self.room = arcade.load_texture(room) if room is not None and room.is_file() else None
        self.floor = None if self.room is not None else room_details(self.style)
        self.board_art = next(prop for prop in props if prop.prop_id == "chopping_board")
        self.props = {prop.prop_id: prop for prop in props if prop.solid}
        self.decorations = {prop_id: tuple(child for child in props if child.support == prop_id)
                            for prop_id in self.props}

    def draw_floor(self):
        if self.room is not None:
            arcade.draw_texture_rect(self.room, arcade.LBWH(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT),
                                     pixelated=True)
        else:
            self.floor.draw()
        for asset, x, y, width, height in WALL_ART:
            draw_pixel_texture(self.textures[asset], arcade.XYWH(x, y, width, height))

    def draw_order(self, foot_y):
        """Back to front, with tabletop decorations attached to their table."""
        entries = [(prop.depth_y, prop.prop_id) for prop in self.props.values()]
        entries.append((foot_y, "player"))
        return [prop_id for _, prop_id in sorted(entries, reverse=True)]

    def draw_prop(self, prop, asset=None):
        draw_pixel_texture(self.textures[asset or prop.asset], arcade.XYWH(*prop.rectangle))

    def draw_food(self, ingredient, x, y, size):
        if ingredient == "chopped_tomato":
            draw_tomato_pieces(x, y, size)
            return
        draw_icon(self.textures[ingredient], x, y, size)

    def draw_plate_food(self, items, x, y, size):
        if len(items) == 1:
            self.draw_food(items[0], x, y, size * (1.7 if items[0] == POT_RECIPE.dish else 1.1))
            return
        for index, ingredient in enumerate(items):
            food_x = x - size * .6 + (index % 2) * size * 1.2
            food_y = y + size * .3 - (index // 2) * size * .65
            self.draw_food(ingredient, food_x, food_y, size)

    def draw_board(self, prop, chopping, state):
        self.draw_prop(prop)
        if chopping is None or chopping.state == "idle":
            return
        # The idle board decal includes a resting knife. Draw the cleared inset
        # over it while a tomato is on the board, before the chef's chop pose.
        x, y, width, height = prop.rectangle
        arcade.draw_lbwh_rectangle_filled(x - width * .24, y - height * .22,
                                          width * .63, height * .55, (193, 110, 61))
        arcade.draw_lbwh_rectangle_filled(x - width * .20, y - height * .17,
                                          width * .55, 1, (168, 91, 48))
        arcade.draw_lbwh_rectangle_filled(x - width * .22, y + height * .23,
                                          width * .58, 1, (218, 135, 79))
        food = "chopped_tomato" if chopping.progress >= .56 else "tomato"
        self.draw_food(food, x + width * .05, y + 1, 19)
        if (chopping.state == "chopping" and state is not None
                and state.plate.location is PlateLocation.CARRIED):
            # During the chopping pose the chef has set the plate beside the board.
            plate_x = x + width * .82
            draw_pixel_texture(self.textures["plate"], arcade.XYWH(plate_x, y, 42, 29))
            self.draw_plate_food(state.plate.ingredients, plate_x, y, 12)

    def draw_pot(self, prop, pot):
        asset = {PotStage.COOKING: "pot_cooking", PotStage.READY: "pot_cooked"}.get(pot.stage)
        self.draw_prop(prop, asset)
        if pot.stage is PotStage.LOADING:
            center = (len(pot.ingredients) - 1) / 2
            for index, ingredient in enumerate(pot.ingredients):
                self.draw_food(ingredient, prop.x + (index - center) * 11, prop.y + 5, 13)
        if pot.stage is PotStage.COOKING:
            elapsed = POT_RECIPE.duration - pot.remaining_seconds
            for index in range(4):
                phase = (elapsed * 2 + index / 4) % 1
                arcade.draw_circle_outline(prop.x - 12 + index * 8 + 2 * sin(phase * 6),
                                           prop.y + 8 + phase * 20, 1 + phase * 2,
                                           (219, 246, 252, int(220 * (1 - phase))), 1)

    def draw_props(self, player, _players, state=None, chopping=None):
        foot_y = player.ground_position[1]
        if chopping is not None and chopping.state == "chopping":
            # The chef works at the left edge. The reaching hand and knife
            # are above this worktop even though the feet sit beside its base.
            foot_y = min(foot_y, self.props["chopping_table"].depth_y - 1)
        for prop_id in self.draw_order(foot_y):
            if prop_id == "player":
                held = state.held if state is not None else None
                hand = player.hand_anchor if held else None
                if held and hand is not None and player.direction == "up":
                    self.draw_food(held, *hand, player.hand_item_size)
                player.draw()
                if state is not None:
                    if state.plate.location is PlateLocation.CARRIED:
                        plate_anchor = player.plate_anchor
                        if plate_anchor is not None:
                            self.draw_plate_food(state.plate.ingredients, *plate_anchor, 16)
                    elif held and hand is not None and player.direction != "up":
                        self.draw_food(held, *hand, player.hand_item_size)
                        player.draw_grip()
                continue
            prop = self.props[prop_id]
            self.draw_prop(prop)
            for decoration in self.decorations[prop_id]:
                if decoration.prop_id == "display_plate" and state is not None:
                    if state.plate.location is PlateLocation.DOCKED:
                        self.draw_prop(decoration)
                        self.draw_plate_food(state.plate.ingredients, decoration.x, decoration.y, 22)
                elif decoration.prop_id == "chopping_board":
                    self.draw_board(decoration, chopping, state)
                elif decoration.prop_id == "display_pot" and state is not None:
                    self.draw_pot(decoration, state.pot)
                else:
                    self.draw_prop(decoration)
