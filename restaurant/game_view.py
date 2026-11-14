"""Compose the player, kitchen, food, service orders, and sound."""
from collections import deque

import arcade

from restaurant.audio import KitchenAudio
from restaurant.display import fit_window, scene_viewport
from restaurant.kitchen.layout import PROPS
from restaurant.kitchen.scene import KitchenScene, draw_icon
from restaurant.ingredients import IngredientSystem
from restaurant.ingredients.models import POT_RECIPE
from restaurant.orders.sidebar import OrderSidebar
from restaurant.orders.system import HAND_SERVICE_ITEMS, OrderSystem
from restaurant.player.controller import PlayerController
from restaurant.player.interaction import choose_target
from restaurant.shared.contracts import ActionResult, PlateLocation, PotStage
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
CRATE_RECTS = {prop.asset.removeprefix("crate_"): prop.rectangle
               for prop in PROPS if prop.asset.startswith("crate_")}
PLATE_TABLE_RECT = next(prop.rectangle for prop in PROPS if prop.prop_id == "plate_counter")


def station_hint(target, state, service_started):
    """Describe the action before the player presses E."""
    carrying = state.plate.location is PlateLocation.CARRIED
    if target.kind == "box":
        item = target.ingredient_id
        return f"E · Add {item} to plate" if carrying else f"E · Pick up {item}"
    if target.kind == "plate":
        if carrying:
            return "E · Return plate"
        return "E · Add held food" if state.held else "E · Pick up plate"
    if target.kind == "pot":
        if state.pot.stage is PotStage.COOKING:
            return "Pot is cooking"
        if state.pot.stage is PotStage.READY:
            if not carrying or state.plate.ingredients:
                return "Bring an empty plate for pasta"
            return "E · Plate pasta"
        return "E · Load pot from plate" if carrying else "E · Add held ingredient"
    if target.kind == "serve":
        if not service_started:
            return "E · Start service"
        if carrying:
            return "E · Serve plate"
        if state.held in HAND_SERVICE_ITEMS:
            return f"E · Serve {state.held}"
        return "Bring a plate, sandwich, or milk"
    if target.kind == "bin":
        return "E · Discard held food" if state.held else "E · Clear plate"
    return "Chopping board · decoration"


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        # The full room and sidebar stay visible in a resizable, DPI-aware window.
        self.camera = arcade.Camera2D(
            viewport=scene_viewport(self.window.width, self.window.height),
            position=(0, 0), projection=arcade.LRBT(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT))
        self.ui_camera = arcade.Camera2D(position=(0, 0))
        self.player = PlayerController(SPAWN)
        self.players = arcade.SpriteList()
        self.players.append(self.player.sprite)
        self.kitchen = KitchenScene()
        self.ingredients = IngredientSystem()
        self.orders = OrderSystem()
        self.sidebar = OrderSidebar(SIDEBAR_BOUNDS)
        self.audio = KitchenAudio()
        self.outgoing = ()
        self.outgoing_seconds = 0.0
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        for x, y, width, height in WALL_RECTANGLES:
            self.walls.append(arcade.SpriteSolidColor(width, height, x, y))
        self.targets = TARGETS
        self.pressed: set[int] = set()
        self.actions = deque()
        self.paused = False
        self.debug = False
        self.selected = None
        self.message = "Use E at the service table to start orders."
        self.interaction_count = 0
        self._text_cache = {}
        self._text_view_size = None

    def clear_input(self):
        self.pressed.clear()
        self.actions.clear()
        self.player.clear_input()

    def on_hide_view(self):
        self.clear_input()
        self.audio.stop()

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
            self.sync_audio()
        elif symbol == arcade.key.M:
            self.audio.muted = not self.audio.muted
            self.sync_audio()
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
        self.ingredients.reset()
        self.orders.reset()
        self.audio.stop()
        self.outgoing = ()
        self.outgoing_seconds = 0.0
        self.player.reset(SPAWN)
        self.paused = False
        self.selected = None
        self.interaction_count = 0
        self.message = "Kitchen reset. Start service at the hatch."

    def on_update(self, delta_time):
        if self.paused:
            return
        self.player.update(delta_time, self.walls)
        self.ingredients.update(delta_time)
        expired = self.orders.stats().expired
        self.orders.update(delta_time)
        if self.orders.stats().expired > expired:
            self.message = "An order expired."
        self.outgoing_seconds = max(0.0, self.outgoing_seconds - delta_time)
        self.selected = choose_target(self.player.position, self.targets)
        while self.actions:
            self.handle_interaction(self.actions.popleft(), self.selected)
        self.sync_audio()

    def sync_audio(self):
        self.audio.sync_bubble(not self.paused and self.ingredients.snapshot().pot.stage is PotStage.COOKING)

    def handle_interaction(self, action, target):
        """Compose task 2 through its public methods; player owns no food state."""
        if target is None:
            self.message = "Move closer to a station marker."
            self.audio.play("reject")
            return
        elif action == "remove" and target.kind != "plate":
            self.message = "Q is the plate-removal hook. Move to the plate."
            self.audio.play("reject")
            return
        self.interaction_count += 1
        state = self.ingredients.snapshot()
        cue = "pickup"
        if target.kind == "chop":
            self.message = "Chopping board ready. Cutting will be connected here later."
            return
        if action == "remove":
            result = self.ingredients.remove_from_plate()
        elif target.kind == "box":
            result = self.ingredients.collect(target.ingredient_id)
            if state.plate.location is PlateLocation.CARRIED:
                cue = "plate"
        elif target.kind == "plate":
            if state.plate.location is PlateLocation.CARRIED:
                result, cue = self.ingredients.return_plate(), "return"
            elif state.held is None:
                result = self.ingredients.pickup_plate()
            else:
                result, cue = self.ingredients.add_to_plate(), "plate"
        elif target.kind == "bin":
            result, cue = self.ingredients.discard(), "return"
        elif target.kind == "pot":
            if state.pot.stage is PotStage.READY:
                result, cue = self.ingredients.take_cooked_portion(), "plate"
            else:
                result, cue = self.ingredients.add_to_pot(), "plate"
        else:
            if not self.orders.started:
                result, cue = self.orders.start(), "accept"
            elif state.plate.location is PlateLocation.CARRIED:
                result, cue = self.orders.try_serve(state.plate, self.ingredients), "serve"
                if result.success:
                    self.outgoing = state.plate.ingredients
                    self.outgoing_seconds = 0.9
            elif state.held is not None:
                result, cue = self.orders.try_serve_held(self.ingredients), "serve"
                if result.success:
                    self.outgoing = (state.held,)
                    self.outgoing_seconds = 0.9
            else:
                result = ActionResult(False, "Bring a plate, sandwich, or milk")
        self.message = f"REMOVE: {result.message}" if action == "remove" else result.message
        self.audio.play(cue if result.success else "reject")

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
        if label.text != value:
            label.text = value
        if label.color != color:
            label.color = color
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
            selected = self.selected == target and target.kind != "chop"
            if selected or self.debug:
                arcade.draw_ellipse_outline(target.x, target.y - 32, 30, 12,
                                            ACCENT if selected else (92, 119, 91), 2)
            if selected:
                self.text("prompt_" + target.target_id, "E", target.x, target.y - 62,
                          14, (34, 72, 60), anchor_x="center")
        state = self.ingredients.snapshot()
        self.kitchen.draw_props(self.player, self.players, state)
        if self.selected and self.selected.kind in ("box", "plate"):
            rectangle = (PLATE_TABLE_RECT if self.selected.kind == "plate"
                         else CRATE_RECTS[self.selected.ingredient_id])
            x, y, width, height = rectangle
            arcade.draw_rect_outline(arcade.XYWH(x, y, width + 6, height + 6),
                                     (34, 90, 68), 3)
        if self.outgoing_seconds:
            progress = 1 - self.outgoing_seconds / 0.9
            for index, food in enumerate(self.outgoing):
                draw_icon(self.kitchen.textures[food], 744 + (index - (len(self.outgoing) - 1) / 2) * 29,
                          558 + progress * 45, 24 * (1 - 0.5 * progress))
        self.text("pass_label", "SERVICE  /  DINING ROOM", 744, 672, 9,
                  (244, 224, 172), anchor_x="center")
        self.text("pantry_label", "PANTRY", 235, 43, 9, (73, 49, 38), anchor_x="center")
        if self.debug:
            for x, y, width, height in WALL_RECTANGLES:
                arcade.draw_rect_outline(arcade.XYWH(x, y, width, height),
                                         (249, 96, 87), 2)
            self.players.draw_hit_boxes(color=(237, 80, 80), line_thickness=2)
            for target in self.targets:
                arcade.draw_circle_outline(target.x, target.y, 64, (80, 140, 130), 1)
        self.sidebar.draw(self.orders.snapshot(), self.orders.stats(), self.kitchen.textures, self.text)
        x = KITCHEN_WIDTH + 18
        hand = "plate" if state.plate.location is PlateLocation.CARRIED else (state.held or "empty").replace("_", " ")
        pot = state.pot.stage.value
        if state.pot.stage is PotStage.COOKING:
            pot = f"cooking ({state.pot.remaining_seconds:.1f}s)"
        plate_load = "Pasta (full)" if POT_RECIPE.dish in state.plate.ingredients else f"{len(state.plate.ingredients)}/4"
        self.text("status", f"Hand: {hand}\nPlate: {plate_load} · {state.plate.location}\nPot: {pot}",
                  x, 245, 12, ACCENT, multiline=True, width=220, anchor_y="top")
        nearby = station_hint(self.selected, state, self.orders.started) if self.selected else "Move near a station"
        self.text("nearby", nearby, x, 169, 12, INK)
        self.text("message", self.message, x, 151, 12, INK,
                  multiline=True, width=220, anchor_y="top")
        self.text("controls", f"WASD / arrows   Move\nE   Use station   Q   Remove food\nP   Pause   R   Reset   Esc   Close\nM   Sound: {'muted' if self.audio.muted else 'on'}   F1   Guides",
                  x, 91, 11, MUTED, multiline=True, width=220, anchor_y="top")
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

    def close(self):
        if isinstance(self.current_view, GameView):
            self.current_view.audio.stop()
        super().close()


def create_window(*, visible=True):
    # Create small and hidden so Windows reports the actual monitor DPI before
    # calculating size. Show only after fitting: no oversized startup window.
    window = DemoWindow(640, 384, "Classic Chef / Kitchen",
                        visible=False, resizable=True,
                        antialiasing=False, update_rate=1 / 60)
    fit_window(window)
    window.show_view(GameView())
    if visible:
        window.set_visible(True)
    return window
