"""Player-only demonstration and the future composition point for teammates."""
from collections import deque
from textwrap import fill

import arcade

from restaurant.kitchen.layout import TARGET_LABELS
from restaurant.kitchen.scene import KitchenScene
from restaurant.player.controller import PlayerController
from restaurant.player.interaction import choose_target
from restaurant.shared.settings import (
    KITCHEN_HEIGHT, KITCHEN_WIDTH, SIDEBAR_BOUNDS, SPAWN, TARGETS,
    WALL_RECTANGLES, WINDOW_HEIGHT, WINDOW_WIDTH,
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
        # Keep a larger world on smaller laptop screens without changing physics.
        self.camera = arcade.Camera2D(
            viewport=arcade.LBWH(0, 0, self.window.width, self.window.height),
            position=(0, 0), projection=arcade.LRBT(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT))
        self.player = PlayerController(SPAWN)
        self.players = arcade.SpriteList()
        self.players.append(self.player.sprite)
        self.kitchen = KitchenScene()
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        for x, y, width, height in WALL_RECTANGLES:
            self.walls.append(arcade.SpriteSolidColor(width, height, x, y))
        self.targets = TARGETS
        self.pressed: set[int] = set()
        self.actions = deque()
        self.paused = False
        self.debug = False
        self.selected = None
        self.message = "Explore the kitchen. The board has its own prep table."
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
            self.message = "Move closer to a station marker."
        elif action == "remove" and target.kind != "plate":
            self.message = "Q is the plate-removal hook. Move to the plate."
        elif target.kind == "chop":
            self.interaction_count += 1
            self.message = "Chopping board ready. Cutting will be connected here later."
        else:
            self.interaction_count += 1
            self.message = f"{action.upper()} -> {target.target_id} (display only)"

    def text(self, key, value, x, y, size=14, color=INK, **kwargs):
        # Reuse text objects instead of recreating them on every frame.
        if key not in self._text_cache:
            self._text_cache[key] = arcade.Text(value, x, y, color, size, **kwargs)
        label = self._text_cache[key]
        label.text = value
        label.draw()

    def on_draw(self):
        self.camera.use()
        self.clear((30, 43, 49))
        self.kitchen.draw_floor()
        self.kitchen.draw_props()
        for target in self.targets:
            selected = self.selected == target
            arcade.draw_circle_filled(target.x, target.y, 7,
                                      ACCENT if selected else (248, 223, 167, 145))
            arcade.draw_circle_outline(target.x, target.y, 14 if selected else 10,
                                       (84, 76, 55), 2)
            if selected:
                self.text("prompt_" + target.target_id, "E", target.x, target.y - 32,
                          14, (34, 72, 60), anchor_x="center")
        arcade.draw_ellipse_filled(self.player.sprite.center_x, self.player.sprite.center_y - 26,
                                  31, 9, (128, 140, 127, 150))
        self.players.draw(pixelated=True)
        if self.debug:
            for x, y, width, height in WALL_RECTANGLES:
                arcade.draw_rect_outline(arcade.XYWH(x, y, width, height),
                                         (249, 96, 87), 2)
            self.players.draw_hit_boxes(color=(237, 80, 80), line_thickness=2)
            for target in self.targets:
                arcade.draw_circle_outline(target.x, target.y, 64, (80, 140, 130), 1)
        arcade.draw_lbwh_rectangle_filled(*SIDEBAR_BOUNDS, (24, 37, 44))
        x = KITCHEN_WIDTH + 24
        top = WINDOW_HEIGHT
        self.text("eyebrow", "EXPANDED KITCHEN / DEMO", x, top - 49, 11, ACCENT)
        self.text("title", "Classic Chef", x, top - 92, 25)
        self.text("subtitle", "The tiled kitchen", x, top - 121, 15, MUTED)
        self.text("controls", "WASD / arrows    Move\nE    Station preview\nQ    Plate preview\nP    Pause / resume\nR    Reset\nF1   Show solid boundaries\nEsc  Close",
                  x, top - 174, 13, INK, multiline=True, width=255, anchor_y="top")
        self.text("status", f"State: {self.player.state}\nFacing: {self.player.direction}\nStation previews: {self.interaction_count}",
                  x, top - 371, 14, ACCENT, multiline=True, width=252, anchor_y="top")
        nearby = TARGET_LABELS[self.selected.target_id] if self.selected else "Explore the room"
        self.text("nearby", nearby, x, top - 484, 18, INK)
        self.text("message", fill(self.message, width=27), x, top - 526, 14, INK,
                  multiline=True, width=250, anchor_y="top")
        self.text("future", "Kitchen props are display only.\nThe chopping table is ready\nfor the future cutting system.\n\nOrders will appear here later.",
                  x, 198, 12, MUTED, multiline=True, width=250, anchor_y="top")
        if self.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT,
                                              (20, 30, 40, 170))
            self.text("paused", "PAUSED  /  P TO RESUME", KITCHEN_WIDTH / 2,
                      KITCHEN_HEIGHT / 2, 24, anchor_x="center")


class DemoWindow(arcade.Window):
    """Forward focus loss so a released key cannot leave the chef moving."""
    def on_deactivate(self):
        if isinstance(self.current_view, GameView):
            self.current_view.clear_input()


def fitted_window_size(display_width, display_height):
    """Leave space for the taskbar/title bar; scale the entire scene uniformly."""
    scale = min(1.0, (display_width - 80) / WINDOW_WIDTH,
                (display_height - 120) / WINDOW_HEIGHT)
    return max(1, round(WINDOW_WIDTH * scale)), max(1, round(WINDOW_HEIGHT * scale))


def create_window(*, visible=True):
    size = fitted_window_size(*arcade.get_display_size())
    window = DemoWindow(*size, "Classic Chef / Tiled Kitchen",
                        visible=visible, antialiasing=False, update_rate=1 / 60)
    window.show_view(GameView())
    return window
