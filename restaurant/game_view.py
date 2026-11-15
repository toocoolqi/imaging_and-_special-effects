"""Compose the player, kitchen, food, service orders, effects and sound.

Each frame: move the chef, advance cooking and chopping, advance order
timers (so an order that just expired cannot be served), route each E/Q
press to one system method, turn order events into effects and sound, then
draw everything from snapshots. One GameView serves all four days.
"""
from collections import deque
from math import ceil

import arcade

from restaurant.audio import KitchenAudio
from restaurant.display import artwork_viewport, fit_window
from restaurant.kitchen.ambience import KitchenAmbience
from restaurant.kitchen.days import DAYS
from restaurant.kitchen.scene import KitchenScene
from restaurant.ingredients import IngredientSystem
from restaurant.ingredients.chopping import ChoppingBoard
from restaurant.ingredients.models import POT_RECIPE
from restaurant.orders.effects import OrderEffects
from restaurant.orders.sidebar import OrderSidebar
from restaurant.orders.system import HAND_SERVICE_ITEMS, OrderSystem
from restaurant.pixel_art import PixelCanvas
from restaurant.player.controller import PlayerController
from restaurant.player.interaction import choose_target
from restaurant.shared.contracts import PlateLocation, PotStage
from restaurant.shared.settings import (
    KITCHEN_HEIGHT, KITCHEN_WIDTH, SPAWN, WINDOW_HEIGHT, WINDOW_WIDTH,
)

MOVE_KEYS = {
    arcade.key.W: "up", arcade.key.UP: "up",
    arcade.key.S: "down", arcade.key.DOWN: "down",
    arcade.key.A: "left", arcade.key.LEFT: "left",
    arcade.key.D: "right", arcade.key.RIGHT: "right",
}
DAY_KEYS = {arcade.key.KEY_1: 0, arcade.key.KEY_2: 1, arcade.key.KEY_3: 2, arcade.key.KEY_4: 3}
INK = (232, 238, 236)
MUTED = (164, 182, 184)
ACCENT = (111, 221, 178)
GOLD = (250, 204, 78)
ORDER_PANEL = (KITCHEN_WIDTH + 8, 250, 240, 370)   # gold meter + three cards
HATCH = (744, 512)                                  # where service effects appear
FADE_SECONDS = 0.6
BANNER_SECONDS = 6.0
LOW_TIME = 10.0


def station_hint(target, state):
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
        if carrying and state.plate.ingredients:
            return "E · Serve plate"
        if state.held in HAND_SERVICE_ITEMS:
            return f"E · Serve {state.held}"
        return "Bring a plate, sandwich, or milk"
    if target.kind == "bin":
        return "E · Discard held food" if state.held else "E · Clear plate"
    return "E · Chop or collect tomato"


class GameView(arcade.View):
    def __init__(self, *, audio_enabled=True, seed=None):
        super().__init__()
        # The full room and sidebar stay visible in a resizable, DPI-aware window.
        self.camera = arcade.Camera2D(
            viewport=artwork_viewport(self.window),
            position=(0, 0), projection=arcade.LRBT(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT))
        self.ui_camera = arcade.Camera2D(position=(0, 0))
        self.art = PixelCanvas(self.window)
        self._frame_labels = []
        self.player = PlayerController(SPAWN)
        self.players = arcade.SpriteList()
        self.players.append(self.player.sprite)
        self.ingredients = IngredientSystem()
        self.chopping = ChoppingBoard()
        self.orders = OrderSystem(seed)
        self.sidebar = OrderSidebar(ORDER_PANEL)
        self.effects = OrderEffects(seed)
        self.audio = KitchenAudio()
        self.audio.muted = not audio_enabled
        self._scenes = {}                 # each kitchen's artwork loads once
        self.day_index = 0
        self.total_gold = 0
        self.finished = False
        self.outgoing = ()
        self.outgoing_seconds = 0.0
        self.pressed: set[int] = set()
        self.actions = deque()
        self.paused = False
        self.debug = False
        self.selected = None
        self.message = ""
        self.interaction_count = 0
        self.fade = 0.0                   # seconds left of the fade-in after a day change
        self.shake = (0.0, 0.0)
        self._text_cache = {}
        self._text_view_size = None
        self.load_day()

    @property
    def day_complete(self):
        return self.orders.is_day_complete

    def load_day(self):
        self.clear_input()
        self.audio.stop()
        self.day = DAYS[self.day_index]
        if self.day.style not in self._scenes:
            self._scenes[self.day.style] = KitchenScene(self.day)
        self.kitchen = self._scenes[self.day.style]
        self.ambience = KitchenAmbience(self.day, self.audio.play)
        self.targets = self.day.targets
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        for x, y, width, height in self.day.walls:
            self.walls.append(arcade.SpriteSolidColor(width, height, x, y))
        self.player.reset(self.day.spawn)
        self.ingredients.reset()
        self.chopping.reset()
        self.orders.reset(rules=self.day.rules)
        self.sidebar.reset()
        self.effects.reset()
        self.outgoing = ()
        self.outgoing_seconds = 0.0
        self.selected = None
        self.banner = BANNER_SECONDS
        self._last_tick = None
        self.message = "Orders are coming in, and each timer starts straight away."
        self.audio.start_music(self.day.music)

    def advance_day(self):
        if self.paused or self.finished or not self.day_complete:
            return
        if self.chopping.state == "chopping":
            return
        if self.ingredients.snapshot().plate.location is PlateLocation.CARRIED:
            self.message = "Return the empty plate before closing the kitchen."
            return
        if self.day_index == len(DAYS) - 1:
            self.finished = True
            self.clear_input()
            self.audio.stop()
            self.effects.celebrate(KITCHEN_WIDTH, KITCHEN_HEIGHT)
        else:
            self.go_to_day(self.day_index + 1)
        self.audio.play("advance")

    def go_to_day(self, index):
        """Change kitchen now and fade in from black."""
        self.day_index = index
        self.finished = self.paused = False
        self.load_day()
        self.fade = FADE_SECONDS
        self.audio.play("transition")

    def clear_input(self):
        self.pressed.clear()
        self.actions.clear()
        self.player.clear_input()

    def on_hide_view(self):
        self.clear_input()
        self.audio.stop_all()

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
        elif symbol == arcade.key.ENTER:
            self.advance_day()
            self.pressed.add(symbol)
        elif symbol == arcade.key.R:
            self.reset()
            self.pressed.add(symbol)
        elif symbol == arcade.key.F1:
            self.debug = not self.debug
        elif symbol in DAY_KEYS:
            self.go_to_day(DAY_KEYS[symbol])
            self.pressed.add(symbol)
        elif not self.paused and not self.finished:
            if symbol in MOVE_KEYS:
                if self.chopping.state != "chopping":
                    self.player.set_move_key(MOVE_KEYS[symbol], True)
            elif symbol in (arcade.key.E, arcade.key.Q):
                self.actions.append("interact" if symbol == arcade.key.E else "remove")

    def on_key_release(self, symbol, modifiers):
        self.pressed.discard(symbol)
        if symbol in MOVE_KEYS:
            direction = MOVE_KEYS[symbol]
            # W and Up can both be held. Releasing one must not release the other.
            still_held = any(MOVE_KEYS.get(key) == direction for key in self.pressed)
            self.player.set_move_key(direction, still_held and self.chopping.state != "chopping")

    def reset(self):
        self.day_index = 0
        self.total_gold = 0
        self.finished = self.paused = False
        self.interaction_count = 0
        self.fade = 0.0
        self.load_day()

    def on_update(self, delta_time):
        if self.paused:
            return
        self.fade = max(0.0, self.fade - delta_time)
        self.effects.update(delta_time)
        if self.finished:
            return
        self.banner = max(0.0, self.banner - delta_time)
        self.player.update(delta_time, self.walls)
        self.ingredients.update(delta_time)
        if self.chopping.update(delta_time):
            self.message = "Tomato chopped. Press E at the board to collect it."
            self.audio.play("plate")
        # Timers before actions: an order that expires this frame cannot be served.
        self.orders.update(delta_time)
        self.outgoing_seconds = max(0.0, self.outgoing_seconds - delta_time)
        self.selected = choose_target(self.player.position, self.targets)
        while self.actions:
            action = self.actions.popleft()
            if self.chopping.state != "chopping":
                self.handle_interaction(action, self.selected)
        self.handle_order_events()
        self.warn_when_time_is_short()
        self.sidebar.update(delta_time, self.orders.snapshot(), self.orders.stats())
        self.ambience.update(delta_time)
        state = self.ingredients.snapshot()
        self.player.set_visual_state(
            held=state.held,
            carrying_plate=state.plate.location is PlateLocation.CARRIED,
            chopping=self.chopping.state == "chopping",
        )
        self.sync_audio()

    def sync_audio(self):
        playing = not self.paused and not self.finished
        self.audio.sync_bubble(playing and self.ingredients.snapshot().pot.stage is PotStage.COOKING)
        self.audio.sync_music(playing)

    def handle_order_events(self):
        """Turn what the order system reported into pictures and sound."""
        for event in self.orders.drain_events():
            self.sidebar.notify(event)
            if event.kind == "arrived":
                self.audio.play("order_bell")
                self.effects.arrived(*HATCH, event.recipe_name)
            elif event.kind == "served":
                self.total_gold += event.gold
                self.audio.play("serve_success")
                self.audio.play("coin")
                self.effects.served(*HATCH, event.gold)
            elif event.kind == "expired":
                self.audio.play("order_expired")
                self.effects.expired(*HATCH)
                self.message = f"Order #{event.order_id} ({event.recipe_name}) expired. No gold."
            elif event.kind == "day_complete":
                self.audio.play("day_complete")
                self.effects.celebrate(KITCHEN_WIDTH, KITCHEN_HEIGHT)
                self.message = "Day complete! Return the plate, then press Enter."

    def warn_when_time_is_short(self):
        """One tick per second while any accepted order has under 10 s left."""
        urgent = [order.remaining_seconds for order in self.orders.snapshot()
                  if order.status == "accepted" and order.remaining_seconds <= LOW_TIME]
        second = ceil(min(urgent)) if urgent else None
        if second is not None and second != self._last_tick:
            self.audio.play("timer_tick")
        self._last_tick = second

    def use_board(self, target):
        if self.chopping.state == "idle":
            work_position = (target.x - 41, target.y + 14)
            previous = self.player.position
            self.player.sprite.position = work_position
            blocked = arcade.check_for_collision_with_list(self.player.sprite, self.walls)
            self.player.sprite.position = previous
            if blocked:
                self.message = "The chef needs room beside the board."
                return
        result = self.chopping.use(self.ingredients)
        if result.success and self.chopping.state == "chopping":
            self.player.sprite.position = work_position
            self.player.clear_input()
            self.player.set_visual_state(chopping=True)
        self.message = result.message
        self.audio.play("plate" if result.success else "reject")

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
        if action == "remove":
            result = self.ingredients.remove_from_plate()
        elif target.kind == "chop":
            self.use_board(target)
            return
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
            self.use_service_hatch(state)
            return
        self.message = f"REMOVE: {result.message}" if action == "remove" else result.message
        self.audio.play(cue if result.success else "reject")

    def use_service_hatch(self, state):
        """E at the hatch: serve the carried plate, or a sandwich or milk by hand.

        Serving and clearing the plate are one transaction inside the order
        system, checked against this exact plate revision, so pressing E
        again can never be paid twice. Success sounds come from order events.
        """
        if self.day_complete:
            self.message = "Day complete! Return the plate, then press Enter."
            return
        if state.plate.location is PlateLocation.CARRIED and state.plate.ingredients:
            result = self.orders.try_serve(state.plate, self.ingredients)
            served = state.plate.ingredients
        elif state.held in HAND_SERVICE_ITEMS:
            result = self.orders.try_serve_held(self.ingredients)
            served = (state.held,)
        else:
            self.message = "Bring a plate, sandwich, or milk to serve an order."
            self.audio.play("reject")
            return
        if result.success:
            self.outgoing, self.outgoing_seconds = served, 0.9
            self.message = f"Sent to the dining room! {result.message}."
        else:
            self.message = f"The dining room sent it back: {result.message.lower()}."
            self.audio.play("serve_fail")
            self.effects.rejected(*HATCH)

    def text(self, key, value, x, y, size=14, color=INK, **kwargs):
        # Keep type out of the pixel-art framebuffer, including order-card text.
        self._frame_labels.append((key, value, x, y, size, color, kwargs))

    def _draw_text(self, key, value, x, y, size, color, kwargs):
        # Rasterize type at its displayed size, instead of shrinking cached
        # world-sized glyphs. This keeps letters intact in letterboxed windows.
        viewport = self.camera.viewport
        ratio = self.window.get_pixel_ratio()
        scale = viewport.width * ratio / WINDOW_WIDTH
        x = viewport.left * ratio + (x - self.shake[0]) * scale
        y = viewport.bottom * ratio + (y - self.shake[1]) * scale
        if "width" in kwargs:
            kwargs["width"] = max(1, int(kwargs["width"] * scale))
        color = tuple(color) if len(color) == 4 else (*color, 255)
        if key not in self._text_cache:
            self._text_cache[key] = arcade.Text(value, x, y, color, size * scale, **kwargs)
        label = self._text_cache[key]
        if label.text != value:
            label.text = value
        if (label.x, label.y) != (x, y):        # animated cards and floating gold move
            label.x, label.y = x, y
        if tuple(label.color) != color:
            label.color = color
        with self.ui_camera.activate():
            label.draw()

    def on_draw(self):
        self.camera.viewport = artwork_viewport(self.window)
        self._frame_labels.clear()
        self.shake = self.effects.shake_offset
        self.art.camera.position = self.shake
        self.art.begin()
        view_size = self.window.width, self.window.height, self.window.scale
        if view_size != self._text_view_size:
            self._text_cache.clear()
            self._text_view_size = view_size
        self.ui_camera.viewport = arcade.LBWH(0, 0, self.window.width, self.window.height)
        ratio = self.window.get_pixel_ratio()
        self.ui_camera.projection = arcade.LRBT(0, self.window.width * ratio,
                                                0, self.window.height * ratio)
        self.kitchen.draw_floor()
        self.ambience.draw_floor_layer()
        foot_x, foot_y = self.player.ground_position
        arcade.draw_ellipse_filled(foot_x, foot_y - 8, 48, 12, (65, 61, 48, 85))
        for target in self.targets:
            selected = self.selected == target
            if selected or self.debug:
                arcade.draw_ellipse_outline(target.x, target.y - 32, 30, 12,
                                            ACCENT if selected else (92, 119, 91), 2)
            if selected:
                self.text("prompt_" + target.target_id, "E", target.x, target.y - 62,
                          14, (34, 72, 60), anchor_x="center")
        state = self.ingredients.snapshot()
        self.kitchen.draw_props(self.player, self.players, state, self.chopping)
        if self.chopping.state == "chopping":
            art = self.kitchen.board_art
            if art is not None:
                arcade.draw_lbwh_rectangle_filled(art.x - 32, art.y + 25, 64, 6, (24, 37, 44))
                arcade.draw_lbwh_rectangle_filled(art.x - 32, art.y + 25,
                                                  64 * self.chopping.progress, 6, ACCENT)
        if self.outgoing_seconds:
            progress = 1 - self.outgoing_seconds / 0.9
            for index, food in enumerate(self.outgoing):
                self.kitchen.draw_food(food, 744 + (index - (len(self.outgoing) - 1) / 2) * 29,
                          558 + progress * 45, 24 * (1 - 0.5 * progress))
        self.effects.draw_hatch_call(*HATCH, not self.day_complete and not self.finished)
        self.ambience.draw_air_layer()
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
        self.draw_sidebar(state)
        self.effects.draw(self.text, (KITCHEN_WIDTH, KITCHEN_HEIGHT))
        self.draw_overlays()
        self.art.present()
        self.ui_camera.use()
        if self.fade < FADE_SECONDS / 2:      # type appears once the fade is half done
            for label in self._frame_labels:
                self._draw_text(*label)

    def draw_sidebar(self, state):
        x = KITCHEN_WIDTH + 16
        arcade.draw_lbwh_rectangle_filled(KITCHEN_WIDTH, 0, WINDOW_WIDTH - KITCHEN_WIDTH,
                                          WINDOW_HEIGHT, (24, 37, 44))
        arcade.draw_lbwh_rectangle_filled(KITCHEN_WIDTH, WINDOW_HEIGHT - 26,
                                          WINDOW_WIDTH - KITCHEN_WIDTH, 26, (18, 28, 34))
        self.text("day", f"Day {self.day_index + 1}/{len(DAYS)} · {self.day.name}",
                  x, WINDOW_HEIGHT - 20, 11, ACCENT)
        self.text("headline", self.day.headline, x, WINDOW_HEIGHT - 58, 15, INK, bold=True)
        self.sidebar.draw(self.orders.snapshot(), self.orders.stats(), self.text,
                          "Kitchen closed. Well done!" if self.day_complete else "Waiting for customers...")
        hand = "plate" if state.plate.location is PlateLocation.CARRIED else (state.held or "empty").replace("_", " ")
        pot = state.pot.stage.value
        if state.pot.stage is PotStage.COOKING:
            pot = f"cooking ({state.pot.remaining_seconds:.1f}s)"
        load = "pasta" if POT_RECIPE.dish in state.plate.ingredients else f"{len(state.plate.ingredients)}/4"
        self.text("status", f"Hand: {hand} · Plate: {load}\nPot: {pot} · Gold total: {self.total_gold}",
                  x, 242, 11, ACCENT, multiline=True, width=224, anchor_y="top")
        nearby = station_hint(self.selected, state) if self.selected else "Move near a station"
        if self.chopping.state == "chopping":
            nearby = "Chopping tomato"
        elif self.day_complete:
            nearby = "Return the plate · Enter"
        self.text("nearby", nearby, x, 186, 11, INK)
        self.text("message", self.message, x, 168, 10, INK, multiline=True, width=224, anchor_y="top")
        sound = "off" if self.audio.muted else "on"
        self.text("controls", f"WASD / arrows  Move    E  Use\nQ  Remove food    P  Pause\n"
                  f"R  Restart    M  Sound {sound}\n1-4  Jump to day    F1  Collisions\nEsc  Close",
                  x, 96, 10, MUTED, multiline=True, width=236, anchor_y="top")

    def draw_overlays(self):
        cx, cy = KITCHEN_WIDTH / 2, KITCHEN_HEIGHT / 2
        if self.banner and not self.paused and not self.finished and not self.day_complete:
            fade = min(1.0, self.banner / 0.8, (BANNER_SECONDS - self.banner) / 0.4 + 0.2)
            alpha = int(255 * max(0.0, fade))
            # Low in the room so the hatch and its "!" call stay visible.
            arcade.draw_lbwh_rectangle_filled(cx - 330, 196, 660, 100, (18, 28, 34, int(alpha * .88)))
            arcade.draw_lbwh_rectangle_filled(cx - 330, 292, 660, 4, GOLD + (alpha,))
            self.text("banner_head", f"DAY {self.day_index + 1}  -  {self.day.headline}", cx, 260, 21,
                      GOLD + (alpha,), anchor_x="center", bold=True)
            self.text("banner_story", self.day.story, cx, 244, 12, INK + (alpha,), multiline=True,
                      width=620, anchor_x="center", anchor_y="top", align="center")
        if self.day_complete and not self.finished:
            # Low in the room, so the plate island and hatch stay in view.
            stats = self.orders.stats()
            arcade.draw_lbwh_rectangle_filled(cx - 250, 190, 500, 128, GOLD)
            arcade.draw_lbwh_rectangle_filled(cx - 247, 193, 494, 122, (24, 37, 44))
            self.text("done_head", f"DAY {self.day_index + 1} COMPLETE!", cx, 276, 24,
                      GOLD, anchor_x="center", bold=True)
            self.text("done_gold", f"Gold {stats.score} / {stats.target}   ·   served {stats.completed}"
                      f"   ·   missed {stats.expired}", cx, 246, 12, INK, anchor_x="center")
            blink = int(self.effects.elapsed * 2.5) % 2 == 0
            self.text("done_key", "Return the plate, then press ENTER", cx, 214, 13,
                      ACCENT if blink else MUTED, anchor_x="center", bold=True)
        if self.finished:
            arcade.draw_lbwh_rectangle_filled(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT,
                                              (20, 30, 40, 220))
            self.effects.draw(self.text, None)          # confetti over the ending
            self.text("ending", "Restaurant Complete", cx, cy + 40, 30, anchor_x="center")
            self.text("ending_story", "From an abandoned kitchen to a flagship restaurant.",
                      cx, cy + 4, 14, ACCENT, anchor_x="center")
            self.text("ending_hint", f"{self.total_gold} gold earned   |   R to play again",
                      cx, cy - 30, 16, anchor_x="center")
        elif self.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, KITCHEN_WIDTH, KITCHEN_HEIGHT,
                                              (20, 30, 40, 170))
            self.text("paused", "PAUSED  /  P TO RESUME", cx, cy, 24, anchor_x="center")
        if self.fade:
            alpha = int(255 * min(1.0, self.fade / FADE_SECONDS) ** 0.7)
            arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, (8, 12, 16, alpha))


class DemoWindow(arcade.Window):
    """Forward focus loss so a released key cannot leave the chef moving."""
    def on_deactivate(self):
        if isinstance(self.current_view, GameView):
            self.current_view.clear_input()

    def close(self):
        if isinstance(self.current_view, GameView):
            self.current_view.audio.stop_all()
        super().close()


def create_window(*, visible=True, show_menu=None, seed=None):
    # Create small and hidden so Windows reports the actual monitor DPI before
    # calculating size. Show only after fitting: no oversized startup window.
    window = DemoWindow(640, 384, "Classic Chef / Kitchen",
                        visible=False, resizable=True,
                        antialiasing=False, update_rate=1 / 60)
    fit_window(window)
    if show_menu is None:
        show_menu = visible
    if show_menu:
        from restaurant.menu import MainMenu
        window.show_view(MainMenu(lambda: window.show_view(GameView(audio_enabled=visible, seed=seed))))
    else:
        window.show_view(GameView(audio_enabled=visible, seed=seed))
    if visible:
        window.set_visible(True)
    return window
