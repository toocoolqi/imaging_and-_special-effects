"""Run the shared kitchen game and route actions between its systems."""
from collections import deque
from math import ceil
from textwrap import fill

import arcade

from restaurant.audio import GameAudio
from restaurant.display import fit_window, scene_viewport
from restaurant.kitchen.days import DAYS
from restaurant.kitchen.layout import TARGET_LABELS
from restaurant.kitchen.scene import KitchenScene
from restaurant.ingredients import IngredientSystem
from restaurant.ingredients.cooking import CookingPot
from restaurant.orders.system import DAY_GOAL, GOLD_PER_ORDER, OrderSystem
from restaurant.player.controller import PlayerController
from restaurant.player.interaction import choose_target
from restaurant.shared.settings import (
    KITCHEN_HEIGHT, KITCHEN_WIDTH, SIDEBAR_BOUNDS, SPAWN, WINDOW_HEIGHT, WINDOW_WIDTH,
)

MOVE_KEYS = {
    arcade.key.W: "up", arcade.key.UP: "up",
    arcade.key.S: "down", arcade.key.DOWN: "down",
    arcade.key.A: "left", arcade.key.LEFT: "left",
    arcade.key.D: "right", arcade.key.RIGHT: "right",
}
INK = (232, 238, 236)
MUTED = (164, 182, 184)
ACCENT = (111, 221, 178)


class GameView(arcade.View):
    def __init__(self, *, audio_enabled=True):
        super().__init__()
        # The full room and sidebar stay visible in a resizable, DPI-aware window.
        self.camera = arcade.Camera2D(
            viewport=scene_viewport(self.window.width, self.window.height),
            position=(0, 0), projection=arcade.LRBT(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT))
        self.ui_camera = arcade.Camera2D(position=(0, 0))
        self.player = PlayerController(SPAWN)
        self.players = arcade.SpriteList()
        self.players.append(self.player.sprite)
        self.ingredients = IngredientSystem()
        self.pot = CookingPot()
        self.orders = OrderSystem()
        self.audio = GameAudio(audio_enabled)
        self.day_index = 0
        self.total_gold = 0
        self.finished = False
        self.serve_flash = 0.0
        self.pressed: set[int] = set()
        self.actions = deque()
        self.paused = False
        self.debug = False
        self.selected = None
        self.message = "Prep at the island, plate up, then use the service hatch."
        self.interaction_count = 0
        self._text_cache = {}
        self._text_view_size = None
        self.load_day()

    @property
    def day_complete(self):
        return self.orders.gold >= DAY_GOAL

    def load_day(self):
        self.clear_input()
        self.audio.set_bubbling(False)
        self.day = DAYS[self.day_index]
        self.kitchen = KitchenScene(self.day)
        self.targets = self.day.targets
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        for x, y, width, height in self.day.walls:
            self.walls.append(arcade.SpriteSolidColor(width, height, x, y))
        self.player.reset(self.day.spawn)
        self.ingredients.reset()
        self.pot.reset()
        self.orders.reset()
        self.serve_flash = 0.0
        self.selected = None
        self.message = "Accept the first order at the service hatch."

    def advance_day(self):
        if self.paused or self.finished or not self.day_complete:
            return
        if self.ingredients.snapshot().carrying_plate:
            self.message = "Return the empty plate before closing the kitchen."
            return
        if self.day_index == len(DAYS) - 1:
            self.finished = True
            self.clear_input()
            self.audio.set_bubbling(False)
        else:
            self.day_index += 1
            self.load_day()
        self.audio.play("advance")

    def clear_input(self):
        self.pressed.clear()
        self.actions.clear()
        self.player.clear_input()

    def on_hide_view(self):
        self.clear_input()
        self.audio.set_bubbling(False)

    def on_key_press(self, symbol, modifiers):
        if symbol in self.pressed:
            return  # Ignore auto-repeat; one action per physical press.
        self.pressed.add(symbol)
        if symbol == arcade.key.ESCAPE:
            self.window.close()
        elif symbol == arcade.key.P:
            self.paused = not self.paused
            self.clear_input()
            self.pressed.add(symbol)
            self.audio.set_bubbling(not self.paused and self.pot.state == "cooking")
            self.message = "Paused" if self.paused else "Resumed."
        elif symbol == arcade.key.M:
            self.audio.toggle()
        elif symbol == arcade.key.ENTER:
            self.advance_day()
            self.pressed.add(symbol)
        elif symbol == arcade.key.R:
            self.reset()
            self.pressed.add(symbol)
        elif symbol == arcade.key.F1:
            self.debug = not self.debug
        elif not self.paused and not self.finished:
            if symbol in MOVE_KEYS:
                self.player.set_move_key(MOVE_KEYS[symbol], True)
            elif symbol in (arcade.key.E, arcade.key.Q):
                self.actions.append("interact" if symbol == arcade.key.E else "remove")

    def on_key_release(self, symbol, modifiers):
        self.pressed.discard(symbol)
        if symbol in MOVE_KEYS:
            direction = MOVE_KEYS[symbol]
            # W and Up can both be held. Releasing one must not release the other.
            still_held = any(MOVE_KEYS.get(key) == direction for key in self.pressed)
            self.player.set_move_key(direction, still_held)

    def reset(self):
        self.day_index = 0
        self.total_gold = 0
        self.finished = self.paused = False
        self.interaction_count = 0
        self.load_day()

    def on_update(self, delta_time):
        if self.paused or self.finished:
            return
        self.serve_flash = max(0, self.serve_flash - delta_time)
        if self.orders.update(delta_time):
            self.message = "Order expired. Accept the replacement at the hatch."
            self.audio.play("reject")
        if self.pot.update(delta_time):
            self.message = "Creamy noodles are ready."
            self.audio.play("ready")
        self.audio.set_bubbling(self.pot.state == "cooking")
        self.player.update(delta_time, self.walls)
        self.selected = choose_target(self.player.position, self.targets)
        while self.actions:
            self.handle_interaction(self.actions.popleft(), self.selected)

    def handle_interaction(self, action, target):
        """Compose task 2 through its public methods; player owns no food state."""
        if target is None:
            self.message = "Move closer to a station marker."
        elif action == "remove" and target.kind != "plate":
            self.message = "Q is the plate-removal hook. Move to the plate."
        elif target.kind == "chop":
            self.interaction_count += 1
            self.message = "Chopping board ready. Cutting will be connected here later."
        elif target.kind == "serve":
            self.interaction_count += 1
            self.use_hatch()
        else:
            self.interaction_count += 1
            if action == "remove":
                result = self.ingredients.remove_from_plate()
                self.message = f"REMOVE: {result.message}"
            elif target.kind == "box":
                result = self.ingredients.collect(target.ingredient_id)
                self.message = result.message
            elif target.kind == "plate":
                result = self.ingredients.use_plate()
                self.message = f"Plate: {result.message}"
            elif target.kind == "bin":
                result = self.ingredients.discard()
                self.message = result.message
            elif target.kind == "pot":
                result = self.pot.use(self.ingredients)
                self.message = result.message
            self.audio.play(("pickup" if target.kind == "box" else "place")
                            if result.success else "reject")

    def use_hatch(self):
        state = self.ingredients.snapshot()
        if self.day_complete:
            self.message = "Return the plate to the island, then press Enter."
            return
        if state.carrying_plate:
            result = self.orders.try_serve(state.plate, self.ingredients.clear_plate)
            self.message = result.message
            if result.success:
                self.total_gold += GOLD_PER_ORDER
                self.serve_flash = 1.1
            self.audio.play("serve" if result.success else "reject")
        elif state.held is None:
            result = self.orders.accept_next()
            self.message = result.message
            self.audio.play("accept" if result.success else "reject")
        else:
            self.message = "Put the ingredient on the plate before serving."
            self.audio.play("reject")

    def text(self, key, value, x, y, size=14, color=INK, **kwargs):
        # Rasterize type at its displayed size, instead of shrinking cached
        # world-sized glyphs. This keeps letters intact in letterboxed windows.
        viewport = self.camera.viewport
        scale = viewport.width / WINDOW_WIDTH
        x, y = viewport.left + x * scale, viewport.bottom + y * scale
        if "width" in kwargs:
            kwargs["width"] = max(1, int(kwargs["width"] * scale))
        if key not in self._text_cache:
            self._text_cache[key] = arcade.Text(value, x, y, color, size * scale, **kwargs)
        label = self._text_cache[key]
        if label.color != color:
            label.color = color
        if label.text != value:
            label.text = value
        with self.ui_camera.activate():
            label.draw()

    def on_draw(self):
        self.clear((30, 43, 49))
        self.camera.viewport = scene_viewport(self.window.width, self.window.height)
        self.camera.use()
        view_size = self.window.width, self.window.height, self.window.scale
        if view_size != self._text_view_size:
            self._text_cache.clear()
            self._text_view_size = view_size
        self.ui_camera.viewport = arcade.LBWH(0, 0, self.window.width, self.window.height)
        self.ui_camera.projection = arcade.LRBT(0, self.window.width, 0, self.window.height)
        self.kitchen.draw_floor()
        foot_x, foot_y = self.player.ground_position
        arcade.draw_ellipse_filled(foot_x, foot_y - 7, 34, 10, (65, 61, 48, 85))
        for target in self.targets:
            selected = self.selected == target
            if selected or self.debug:
                arcade.draw_ellipse_outline(target.x, target.y - 32, 30, 12,
                                            ACCENT if selected else (92, 119, 91), 2)
            if selected:
                self.text("prompt_" + target.target_id, "E", target.x, target.y - 62,
                          14, (34, 72, 60), anchor_x="center")
        state = self.ingredients.snapshot()
        self.kitchen.draw_props(self.player, self.players, state, self.pot)
        if self.serve_flash:
            arcade.draw_circle_outline(744, 547, 12 + (1.1 - self.serve_flash) * 48,
                                       (249, 207, 98, int(240 * self.serve_flash / 1.1)), 3)
        self.text("pass_label", "SERVICE  /  DINING ROOM", 744, 672, 9,
                  (244, 224, 172), anchor_x="center")
        self.text("pantry_label", "PANTRY", 235, 43, 9, (73, 49, 38), anchor_x="center")
        if self.debug:
            for x, y, width, height in self.day.walls:
                arcade.draw_rect_outline(arcade.XYWH(x, y, width, height),
                                         (249, 96, 87), 2)
            self.players.draw_hit_boxes(color=(237, 80, 80), line_thickness=2)
            for target in self.targets:
                arcade.draw_circle_outline(target.x, target.y, 64, (80, 140, 130), 1)
        arcade.draw_lbwh_rectangle_filled(*SIDEBAR_BOUNDS, (24, 37, 44))
        x = KITCHEN_WIDTH + 18
        top = WINDOW_HEIGHT
        self.text("eyebrow", f"DAY {self.day_index + 1} / {len(DAYS)}", x, top - 35, 11, ACCENT)
        self.text("title", "Classic Chef", x, top - 76, 24)
        self.text("subtitle", self.day.name, x, top - 105, 14, MUTED)
        ticket = self.orders.snapshot()
        phase = f"{ceil(ticket.remaining_seconds)} s left" if self.orders.active else "Accept at the hatch"
        if self.day_complete:
            phase = "Return the plate and press Enter"
        self.text("order", f"{ticket.recipe_name}\n{phase}", x, top - 143, 15, INK,
                  multiline=True, width=225, anchor_y="top")
        for index, food in enumerate(ticket.required if not self.day_complete else ()):
            texture = self.kitchen.textures[food]
            scale = 33 / max(texture.width, texture.height)
            arcade.draw_texture_rect(texture, arcade.XYWH(x + 17 + 42 * index,
                top - 221, texture.width * scale, texture.height * scale), pixelated=False)
        self.text("gold", f"Gold {self.orders.gold} / {DAY_GOAL}   |   Total {self.total_gold}",
                  x, top - 270, 13, (249, 207, 98))
        hand = "plate" if state.carrying_plate else (state.held or "empty").replace("_", " ")
        self.text("status", f"Hand: {hand}\nPlate: {len(state.plate.ingredients)}/4\n"
                  f"Pot: {self.pot.state}  |  Served: {self.orders.completed}",
                  x, top - 314, 13, ACCENT, multiline=True, width=225, anchor_y="top")
        nearby = TARGET_LABELS[self.selected.target_id] if self.selected else "Explore the room"
        self.text("nearby", nearby, x, top - 412, 18, INK)
        self.text("message", fill(self.message, width=26), x, top - 446, 13, INK,
                  multiline=True, width=220, anchor_y="top")
        sound = "off" if self.audio.muted else "on"
        self.text("controls", f"WASD / arrows   Move\nE   Use station   Q   Remove food\n"
                  f"P   Pause   R   Restart   M   Sound {sound}\nF1   Collisions   Esc   Close",
                  x, 119, 11, MUTED, multiline=True, width=224, anchor_y="top")
        if self.finished:
            arcade.draw_lbwh_rectangle_filled(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT,
                                              (20, 30, 40, 220))
            self.text("ending", "Restaurant Complete", KITCHEN_WIDTH / 2,
                      KITCHEN_HEIGHT / 2 + 24, 30, anchor_x="center")
            self.text("ending_hint", f"{self.total_gold} gold earned   |   R to play again",
                      KITCHEN_WIDTH / 2, KITCHEN_HEIGHT / 2 - 20, 16, anchor_x="center")
        elif self.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT,
                                              (20, 30, 40, 170))
            self.text("paused", "PAUSED  /  P TO RESUME", KITCHEN_WIDTH / 2,
                      KITCHEN_HEIGHT / 2, 24, anchor_x="center")


class DemoWindow(arcade.Window):
    """Forward focus loss so a released key cannot leave the chef moving."""
    def on_deactivate(self):
        if isinstance(self.current_view, GameView):
            self.current_view.clear_input()


def create_window(*, visible=True):
    # Create small and hidden so Windows reports the actual monitor DPI before
    # calculating size. Show only after fitting: no oversized startup window.
    window = DemoWindow(640, 384, "Classic Chef / Kitchen",
                        visible=False, resizable=True,
                        antialiasing=False, update_rate=1 / 60)
    fit_window(window)
    window.show_view(GameView(audio_enabled=visible))
    if visible:
        window.set_visible(True)
    return window
