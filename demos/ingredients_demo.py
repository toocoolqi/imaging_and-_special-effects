"""Run python -m demos.ingredients_demo to exercise Member 2 independently."""
import arcade

from restaurant.ingredients import IngredientSystem
from restaurant.ingredients.renderer import IngredientRenderer
from restaurant.shared.contracts import ActionResult, InteractionTarget

TARGETS = (
    InteractionTarget("box_sandwich", "box", 130, 465, "sandwich"),
    InteractionTarget("box_tomato", "box", 330, 465, "tomato"),
    InteractionTarget("box_noodles", "box", 530, 465, "noodles"),
    InteractionTarget("box_milk", "box", 730, 465, "milk"),
    InteractionTarget("plate", "plate", 480, 235),
)
COLLECT_KEYS = {
    arcade.key.KEY_1: "sandwich", arcade.key.KEY_2: "tomato",
    arcade.key.KEY_3: "noodles", arcade.key.KEY_4: "milk",
}
INK = (238, 241, 231)
MUTED = (166, 186, 180)
ACCENT = (123, 223, 173)


class IngredientsDemo(arcade.View):
    def __init__(self):
        super().__init__()
        self.system = IngredientSystem()
        self.renderer = IngredientRenderer()
        self.latest = ActionResult(True, "Press 1-4 to collect an ingredient")
        self.pressed = set()
        self._labels = {}

    def on_key_press(self, symbol, modifiers):
        if symbol in self.pressed:
            return
        self.pressed.add(symbol)
        if symbol == arcade.key.ESCAPE:
            self.window.close()
        elif symbol in COLLECT_KEYS:
            self.latest = self.system.collect(COLLECT_KEYS[symbol])
        elif symbol == arcade.key.A:
            self.latest = self.system.add_to_plate()
        elif symbol == arcade.key.Q:
            self.latest = self.system.remove_from_plate()
        elif symbol == arcade.key.B:
            self.latest = self.system.discard()
        elif symbol == arcade.key.R:
            self.system.reset()
            self.latest = ActionResult(True, "Session reset")

    def on_key_release(self, symbol, modifiers):
        self.pressed.discard(symbol)

    def on_hide_view(self):
        self.pressed.clear()

    def _text(self, key, value, x, y, size=14, color=INK, width=260):
        if key not in self._labels:
            self._labels[key] = arcade.Text(
                value, x, y, color, size, width=width,
                multiline=True, anchor_y="top",
            )
        label = self._labels[key]
        label.text, label.color = value, color
        label.draw()

    def on_draw(self):
        self.clear((32, 47, 48))
        arcade.draw_lbwh_rectangle_filled(900, 0, 300, 720, (23, 34, 39))
        self._text("eyebrow", "MEMBER 2 / INGREDIENT LAB", 40, 684, 12, ACCENT, 800)
        self._text("title", "Build a plate", 40, 656, 28, width=800)
        self._text("intro", "Collect one item, add it, then try removing or discarding it.", 40, 612, 13, MUTED, 800)
        for index, target in enumerate(TARGETS[:4], 1):
            self._text(f"key{index}", f"[{index}] Collect", target.x - 39, 435, 12, ACCENT, 150)
        arcade.draw_circle_outline(145, 185, 35, (99, 135, 121), 2)
        self._text("hand_station", "HELD ITEM", 96, 124, 12, MUTED, 180)
        state = self.system.snapshot()
        self.renderer.draw(state, (130, 185), TARGETS)
        self._text("controls_title", "Controls", 924, 674, 22)
        self._text("controls", "1  Sandwich\n2  Tomato\n3  Noodles\n4  Milk\n\nA  Add to plate\nQ  Remove latest\nB  Discard\nR  Reset\nEsc  Close", 924, 627, 14)
        self._text("state", f"Hand: {state.held or 'empty'}\nPlate: {len(state.plate.ingredients)}/4\nRevision: {state.plate.revision}", 924, 368, 15, ACCENT)
        self._text("feedback_title", "LATEST ACTION", 924, 258, 11, MUTED)
        prefix = "OK" if self.latest.success else "BLOCKED"
        self._text("feedback", f"{prefix}: {self.latest.message}", 924, 232, 15,
                   ACCENT if self.latest.success else (255, 173, 131))
        self._text("note", "Bin rule: discard held food first; otherwise clear the plate.\n\nCollect duplicates to test quantities. The plate holds up to four items.", 40, 85, 12, MUTED, 800)


class IngredientsWindow(arcade.Window):
    def on_deactivate(self):
        if isinstance(self.current_view, IngredientsDemo):
            self.current_view.pressed.clear()


def create_window(*, visible=True):
    window = IngredientsWindow(
        1200, 720, "Restaurant / Ingredient and Plate Demo",
        visible=visible, antialiasing=False,
    )
    window.show_view(IngredientsDemo())
    return window


def main():
    create_window()
    arcade.run()


if __name__ == "__main__":
    main()
