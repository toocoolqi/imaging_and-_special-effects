"""Player-only demonstration and the future composition point for teammates."""
from collections import deque
from textwrap import fill

import arcade

from restaurant.player.controller import PlayerController
from restaurant.player.interaction import choose_target
from restaurant.shared.settings import (
    SPAWN, TARGETS, WALL_RECTANGLES, WINDOW_HEIGHT, WINDOW_WIDTH,
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
    def __init__(self):
        super().__init__()
        self.player = PlayerController(SPAWN)
        self.players = arcade.SpriteList()
        self.players.append(self.player.sprite)
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        for x, y, width, height in WALL_RECTANGLES:
            color = (55, 76, 81) if width < 30 or height < 30 else (80, 112, 114)
            self.walls.append(arcade.SpriteSolidColor(width, height, x, y, color))
        self.targets = TARGETS
        self.pressed: set[int] = set()
        self.actions = deque()
        self.paused = False
        self.debug = False
        self.selected = None
        self.message = "Walk to a floor marker, then press E."
        self.interaction_count = 0
        self._text_cache = {}

    def clear_input(self):
        self.pressed.clear()
        self.actions.clear()
        self.player.clear_input()

    def on_hide_view(self):
        self.clear_input()

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
            self.message = "Paused" if self.paused else "Resumed. Press movement keys again."
        elif symbol == arcade.key.R:
            self.reset()
            self.pressed.add(symbol)
        elif symbol == arcade.key.F1:
            self.debug = not self.debug
        elif not self.paused:
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
        self.clear_input()
        self.player.reset(SPAWN)
        self.paused = False
        self.selected = None
        self.interaction_count = 0
        self.message = "Player demo reset."

    def on_update(self, delta_time):
        if self.paused:
            return
        self.player.update(delta_time, self.walls)
        self.selected = choose_target(self.player.position, self.targets)
        while self.actions:
            self.handle_interaction(self.actions.popleft(), self.selected)

    def handle_interaction(self, action, target):
        """Replace this demo feedback with Member 2/3 public API calls later.

        This is the single routing hook; the player never owns food/order state.
        """
        if target is None:
            self.message = "Move closer to a floor marker."
        elif action == "remove" and target.kind != "plate":
            self.message = "Q is the plate-removal hook. Move to the plate."
        else:
            self.interaction_count += 1
            self.message = f"{action.upper()} -> {target.target_id} (demo only)"

    def text(self, key, value, x, y, size=14, color=INK, **kwargs):
        # Reuse text objects instead of recreating them on every frame.
        if key not in self._text_cache:
            self._text_cache[key] = arcade.Text(value, x, y, color, size, **kwargs)
        label = self._text_cache[key]
        label.text = value
        label.draw()

    def on_draw(self):
        self.clear((30, 43, 49))
        arcade.draw_lbwh_rectangle_filled(20, 20, 860, 680, (223, 222, 207))
        for x in range(20, 881, 40):
            arcade.draw_line(x, 20, x, 700, (206, 207, 192), 1)
        for y in range(20, 701, 40):
            arcade.draw_line(20, y, 880, y, (206, 207, 192), 1)
        self.walls.draw()
        for i, name in enumerate(("SANDWICH", "TOMATO", "NOODLES", "MILK")):
            self.text(f"box{i}", name, 130 + i * 190, 600, 13, anchor_x="center", anchor_y="center")
        for name, x, y in (("PLATE", 450, 360), ("BIN", 130, 120), ("SERVE", 750, 120)):
            self.text(name, name, x, y, 14, anchor_x="center", anchor_y="center")
        for target in self.targets:
            selected = self.selected == target
            arcade.draw_circle_filled(target.x, target.y, 9, ACCENT if selected else (150, 170, 158))
            arcade.draw_circle_outline(target.x, target.y, 15 if selected else 12, (70, 102, 91), 2)
            if selected:
                self.text("prompt_" + target.target_id, "E", target.x, target.y - 32,
                          13, (34, 72, 60), anchor_x="center")
        arcade.draw_ellipse_filled(self.player.sprite.center_x, self.player.sprite.center_y - 26,
                                  31, 9, (128, 140, 127, 150))
        self.players.draw(pixelated=True)
        if self.debug:
            self.players.draw_hit_boxes(color=(237, 80, 80), line_thickness=2)
            for target in self.targets:
                arcade.draw_circle_outline(target.x, target.y, 64, (80, 140, 130), 1)
        arcade.draw_lbwh_rectangle_filled(900, 0, 300, 720, (24, 37, 44))
        self.text("eyebrow", "MEMBER 1 / PLAYABLE DEMO", 924, 671, 11, ACCENT)
        self.text("title", "Classic Chef", 924, 628, 25)
        self.text("subtitle", "Player system", 924, 599, 15, MUTED)
        self.text("controls", "WASD / arrows    Move\nE    Interact\nQ    Plate-removal intent\nP    Pause / resume\nR    Reset\nF1   Collision / range guide\nEsc  Close",
                  924, 546, 13, INK, multiline=True, width=255, anchor_y="top")
        self.text("status", f"State: {self.player.state}\nFacing: {self.player.direction}\nHook calls: {self.interaction_count}",
                  924, 349, 14, ACCENT, multiline=True, width=252, anchor_y="top")
        self.text("message", fill(self.message, width=27), 924, 244, 14, INK,
                  multiline=True, width=250, anchor_y="top")
        self.text("future", "Orders will live here later.\nStations currently send\ninteraction events only.",
                  924, 118, 12, MUTED, multiline=True, width=250, anchor_y="top")
        if self.paused:
            arcade.draw_lbwh_rectangle_filled(20, 20, 860, 680, (20, 30, 40, 170))
            self.text("paused", "PAUSED  /  P TO RESUME", 450, 450, 24, anchor_x="center")


class DemoWindow(arcade.Window):
    """Forward focus loss so a released key cannot leave the chef moving."""
    def on_deactivate(self):
        if isinstance(self.current_view, GameView):
            self.current_view.clear_input()


def create_window(*, visible=True):
    window = DemoWindow(WINDOW_WIDTH, WINDOW_HEIGHT, "Restaurant / Player System",
                        visible=visible, antialiasing=False, update_rate=1 / 60)
    window.show_view(GameView())
    return window
