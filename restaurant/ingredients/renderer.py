"""Read-only ingredient visuals; gameplay state belongs to IngredientSystem."""
from pathlib import Path

import arcade

from restaurant.ingredients.models import PLATE_CAPACITY
from restaurant.shared.contracts import IngredientSnapshot, InteractionTarget

INK = (238, 241, 231)
COLORS = {
    "sandwich": (205, 155, 98), "tomato": (233, 92, 73),
    "noodles": (248, 205, 81), "milk": (114, 168, 224),
}
ASSET_DIRECTORY = Path(__file__).resolve().parents[2] / "assets" / "ingredients" / "sprites"


class IngredientRenderer:
    """Draw supplied snapshots with artwork when present and labeled fallbacks."""

    def __init__(self):
        self._textures = {}
        self._labels = {}
        names = (*COLORS, *(f"box_{ingredient}" for ingredient in COLORS), "plate")
        for name in names:
            path = ASSET_DIRECTORY / f"{name}.png"
            if path.is_file():
                self._textures[name] = arcade.load_texture(path)

    def _text(self, key, value, x, y, size=12, color=INK):
        if key not in self._labels:
            self._labels[key] = arcade.Text(
                value, x, y, color, size, anchor_x="center", anchor_y="center",
            )
        label = self._labels[key]
        label.text, label.x, label.y, label.color = value, x, y, color
        label.draw()

    def _image(self, name, x, y, width, height):
        texture = self._textures.get(name)
        if texture is None:
            return False
        scale = min(width / texture.width, height / texture.height)
        arcade.draw_texture_rect(
            texture, arcade.XYWH(x, y, texture.width * scale, texture.height * scale),
            pixelated=True,
        )
        return True

    def _ingredient(self, key, ingredient, x, y, size=36):
        if not self._image(ingredient, x, y, size, size):
            arcade.draw_lbwh_rectangle_filled(
                x - size / 2, y - size / 2, size, size, COLORS[ingredient],
            )
            self._text(key, ingredient[0].upper(), x, y, 14, (36, 45, 41))

    def draw(
        self, state: IngredientSnapshot, player_position: tuple[float, float],
        targets: tuple[InteractionTarget, ...],
    ) -> None:
        for target in targets:
            x, y = target.x, target.y
            if target.kind == "box":
                ingredient = target.ingredient_id
                if not self._image(f"box_{ingredient}", x, y + 80, 130, 100):
                    arcade.draw_lbwh_rectangle_filled(x - 65, y + 35, 130, 90, (92, 69, 51))
                    self._ingredient(target.target_id, ingredient, x, y + 85, 42)
                self._text(target.target_id + "_name", ingredient.upper(), x, y + 15)
            elif target.kind == "plate":
                if not self._image("plate", x, y + 85, 250, 160):
                    arcade.draw_ellipse_filled(x, y + 85, 250, 160, (226, 221, 204))
                for index in range(PLATE_CAPACITY):
                    slot_x = x - 78 + index * 52
                    arcade.draw_circle_outline(slot_x, y + 85, 23, (167, 160, 144), 1)
                    if index < len(state.plate.ingredients):
                        self._ingredient(f"slot{index}", state.plate.ingredients[index], slot_x, y + 85)
                    self._text(f"slot_number{index}", str(index + 1), slot_x, y + 48, 10, (65, 65, 59))
                self._text("capacity", f"PLATE  {len(state.plate.ingredients)}/{PLATE_CAPACITY}", x, y - 12)
                contents = " > ".join(state.plate.ingredients) or "Empty"
                self._text("contents", contents, x, y - 35, 11)

        x, y = player_position
        if state.held is not None:
            self._ingredient("held_icon", state.held, x + 48, y + 28)
        self._text("held_label", f"Hand: {state.held or 'empty'}", x + 48, y - 14)
