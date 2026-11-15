"""Run python -m demos.orders_demo to exercise the order system on its own.

No chef, kitchen or ingredient system is needed: the demo hands OrderSystem
handmade PlateSnapshot records, exactly as the real game will hand it the
real plate. Use it to see every order effect and sound in isolation.
"""
import arcade

from restaurant.audio import KitchenAudio
from restaurant.orders import DayRules, OrderSystem
from restaurant.orders.effects import OrderEffects
from restaurant.orders.sidebar import OrderSidebar
from restaurant.shared.contracts import ActionResult, PlateSnapshot

WIDTH, HEIGHT = 1000, 640
PANEL = (WIDTH - 256, 150, 240, 370)
HATCH = (360, 250)
RULES = DayRules(target_gold=250, patience_seconds=45.0, arrival_seconds=8.0,
                 recipe_ids=("tomato_sandwich", "lunch_set", "pasta"))
INK = (238, 241, 231)
MUTED = (166, 186, 180)
ACCENT = (123, 223, 173)
WARN = (255, 173, 131)


class OrdersDemo(arcade.View):
    def __init__(self, *, sound: bool = True, seed: int | None = 7):
        super().__init__()
        self.seed = seed
        self.system = OrderSystem(seed, RULES)
        self.sidebar = OrderSidebar(PANEL)
        self.effects = OrderEffects(seed)
        self.sound = KitchenAudio()
        self.sound.muted = not sound
        self.latest = ActionResult(True, "An order is in: press C to serve it")
        self.paused = False
        self.revision = 0            # pretend plate revision, grows with each submission
        self.pressed = set()
        self._labels = {}

    # ------------------------------------------------------------ helpers
    def _oldest(self):
        return next(iter(self.system.snapshot()), None)

    def _submit(self, ingredients):
        self.revision += 1
        result = self.system.try_serve(PlateSnapshot(tuple(ingredients), self.revision))
        self.latest = ActionResult(result.success, result.message)
        if not result.success:
            self.sound.play("serve_fail")
            self.effects.rejected(*HATCH)

    def _events(self):
        for event in self.system.drain_events():
            self.sidebar.notify(event)
            if event.kind == "arrived":
                self.sound.play("order_bell")
                self.effects.arrived(*HATCH, event.recipe_name)
            elif event.kind == "served":
                self.sound.play("serve_success")
                self.effects.served(*HATCH, event.gold)
            elif event.kind == "expired":
                self.sound.play("order_expired")
                self.effects.expired(*HATCH)
                self.latest = ActionResult(False, f"Order #{event.order_id} expired")
            elif event.kind == "day_complete":
                self.sound.play("day_complete")
                self.effects.celebrate(WIDTH - 256, HEIGHT)
                self.latest = ActionResult(True, f"Day complete with {event.gold} gold. Press R")

    # ------------------------------------------------------------ input
    def on_key_press(self, symbol, modifiers):
        if symbol in self.pressed:
            return  # one action per physical press
        self.pressed.add(symbol)
        if symbol == arcade.key.ESCAPE:
            self.window.close()
        elif symbol == arcade.key.M:
            self.sound.muted = not self.sound.muted
            self.latest = ActionResult(True, "Muted" if self.sound.muted else "Sound on")
        elif symbol == arcade.key.R:
            self.system.reset(self.seed)
            self.sidebar.reset()
            self.effects.reset()
            self.paused = False
            self.latest = ActionResult(True, "New day started")
        elif symbol == arcade.key.P:
            self.paused = not self.paused
            self.latest = ActionResult(True, "Paused: timers frozen" if self.paused else "Resumed")
        elif self.paused:
            return
        elif symbol == arcade.key.C:
            order = self._oldest()
            if order is not None:
                self._submit(reversed(order.required))  # order of items must not matter
        elif symbol == arcade.key.W:
            order = self._oldest()
            extra = (order.required if order else ()) + ("milk",)
            self._submit(extra)                         # one extra item: must be refused
        elif symbol in (arcade.key.T, arcade.key.Y):
            self.advance(10.0 if symbol == arcade.key.T else 60.0)
        self._events()

    def on_key_release(self, symbol, modifiers):
        self.pressed.discard(symbol)

    def on_hide_view(self):
        self.pressed.clear()

    # ------------------------------------------------------------ frame
    def advance(self, seconds):
        """Explicit time skip (T / Y keys) so expiry can be shown on demand."""
        self.system.update(seconds)
        self._events()

    def on_update(self, delta_time):
        if not self.paused:
            self.system.update(delta_time)
            self._events()
            self.effects.update(delta_time)
            self.sidebar.update(delta_time, self.system.snapshot())

    def _text(self, key, value, x, y, size=14, color=INK, width=560):
        if key not in self._labels:
            self._labels[key] = arcade.Text(value, x, y, color, size, width=width,
                                            multiline=True, anchor_y="top")
        label = self._labels[key]
        label.text, label.color = value, color
        label.draw()

    def on_draw(self):
        self.clear((32, 47, 48))
        dx, dy = self.effects.shake_offset
        arcade.draw_lbwh_rectangle_filled(WIDTH - 264 + dx, dy, 264, HEIGHT, (23, 34, 39))
        self._text("eyebrow", "ORDER SYSTEM LAB", 40, 612, 12, ACCENT)
        self._text("title", "Serve plates before the timers run out", 40, 586, 24)
        self._text("intro", "Orders arrive on their own and each timer starts at once. "
                   "A faster delivery pays a bigger tip.", 40, 544, 13, MUTED)
        self._text("controls",
                   "C   Serve a CORRECT plate (items in reverse order)\n"
                   "W   Serve a WRONG plate (one extra milk)\n"
                   "T   Skip 10 seconds        Y   Skip 60 seconds\n"
                   "P   Pause / resume          R   New day\n"
                   "M   Mute                    Esc Close", 40, 486, 14)
        # A stand-in service hatch where the world effects appear.
        hx, hy = HATCH[0] + dx, HATCH[1] + dy
        arcade.draw_lbwh_rectangle_filled(hx - 130, hy - 34, 260, 68, (104, 70, 52))
        arcade.draw_lbwh_rectangle_filled(hx - 122, hy - 26, 244, 52, (34, 50, 46))
        self._text("hatch", "SERVICE HATCH", hx - 58, hy + 8, 12, MUTED, 200)
        self.effects.draw_hatch_call(hx, hy - 40)
        stats = self.system.stats()
        self._text("stats", f"arrived {stats.accepted}    served {stats.completed}    "
                   f"expired {stats.expired}    gold {stats.score} / {stats.target}", 40, 150, 14, ACCENT)
        prefix = "OK" if self.latest.success else "REFUSED"
        self._text("latest", f"{prefix}: {self.latest.message}", 40, 116, 16,
                   ACCENT if self.latest.success else WARN)
        self._text("rule", "arrived = served + expired + still on the board.   "
                   "Wrong plates never change orders, gold or the plate.", 40, 70, 11, MUTED)
        self.sidebar.left = PANEL[0] + dx
        self.sidebar.bottom = PANEL[1] + dy
        self.sidebar.draw(self.system.snapshot(), stats)
        self.effects.draw(None, (WIDTH - 264, HEIGHT))
        if self.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, WIDTH, HEIGHT, (20, 30, 40, 150))
            self._text("paused", "PAUSED  /  P TO RESUME", WIDTH / 2 - 150, HEIGHT / 2 + 14, 22, width=400)


class OrdersWindow(arcade.Window):
    def on_deactivate(self):
        if isinstance(self.current_view, OrdersDemo):
            self.current_view.pressed.clear()


def create_window(*, visible=True):
    window = OrdersWindow(WIDTH, HEIGHT, "Restaurant / Order System Demo",
                          visible=visible, antialiasing=False)
    window.show_view(OrdersDemo(sound=visible))
    return window


def main():
    create_window()
    arcade.run()


if __name__ == "__main__":
    main()
