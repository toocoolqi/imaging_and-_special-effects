"""Animated order panel: gold meter plus up to three order cards (Arcade).

Shapes and icons are drawn into the game's pixel-art canvas; every label goes
through the `text` callback so type stays sharp at screen resolution.

The panel never decides anything. OrderSystem owns orders, timers and gold;
this class receives immutable snapshots and draws them. The only state kept
here is presentation state: where a card currently is while it slides, how
long a "SERVED" banner has been showing, the number the gold counter is
counting up through.

Effects (and the tutorial each technique comes from)
- Cards slide in from the right and close gaps smoothly   [Week 3 movement]
- Timer bar goes green -> amber -> red, blinks under 10 s  [Week 10 blink]
- A newly arrived card glows gold for a moment              [Week 8 lighting]
- Served card flashes green; expired card turns greyscale
  (Pillow image processing -> arcade.Texture) and shakes    [Weeks 7, 10]
- Gold number counts up and the coin pops on each payment   [Week 4 animation]
"""
from collections import Counter
from math import ceil, sin
from pathlib import Path

import arcade
from PIL import ImageEnhance, ImageOps

from restaurant.pixel_art import draw_pixel_texture
from restaurant.shared.contracts import OrderEvent, OrderSnapshot, OrderStats

FOOD_DIR = Path(__file__).resolve().parents[2] / "assets" / "ingredients" / "sprites"
FOOD_NAMES = ("sandwich", "tomato", "noodles", "milk", "pasta")
FOOD_COLORS = {"sandwich": (214, 170, 96), "tomato": (214, 72, 60), "noodles": (236, 200, 110),
               "milk": (120, 170, 232), "pasta": (232, 176, 92), "chopped_tomato": (214, 72, 60)}

PANEL = (30, 44, 52)
CARD = (44, 62, 72)
CARD_EDGE = (70, 94, 106)
INK = (236, 240, 236)
MUTED = (160, 178, 182)
GOLD = (250, 204, 78)
GOLD_DARK = (176, 128, 36)
GREEN = (104, 214, 150)
AMBER = (244, 182, 66)
RED = (236, 88, 78)

GOLD_HEIGHT = 62
CARD_HEIGHT = 94
CARD_GAP = 6
LOW_TIME = 10.0          # seconds: the card starts blinking
GHOST_SECONDS = 1.1      # how long a served/expired card lingers
NEW_SECONDS = 1.8        # how long a newly arrived card glows


def timer_color(fraction: float):
    """Green above half, amber above a quarter, red below."""
    return GREEN if fraction > 0.5 else AMBER if fraction > 0.25 else RED


def blink_on(elapsed: float, per_second: float = 5.0) -> bool:
    """Square-wave blink: on for half of each cycle (Week 10 technique)."""
    return int(elapsed * per_second) % 2 == 0


def greyscale_texture(texture: arcade.Texture) -> arcade.Texture:
    """Image processing with Pillow: drain the colour, dim it, keep the alpha."""
    image = texture.image.convert("RGBA")
    grey = ImageOps.grayscale(image.convert("RGB")).convert("RGBA")
    grey = ImageEnhance.Brightness(grey).enhance(0.75)
    grey.putalpha(image.getchannel("A"))
    return arcade.Texture(grey)


class _Card:
    """Where one card is drawn right now (animation only)."""

    def __init__(self, slide: float):
        self.y = None            # current bottom edge, eases towards target_y
        self.target_y = 0.0      # the slot this card belongs in
        self.slide = slide       # horizontal offset, eases to 0
        self.ghost = None        # None, "served" or "expired"
        self.ghost_age = 0.0
        self.age = 0.0           # seconds since the order arrived (for its glow)
        self.gold = 0
        self.snapshot: OrderSnapshot | None = None


class OrderSidebar:
    def __init__(self, bounds: tuple[int, int, int, int]):
        self.left, self.bottom, self.width, self.height = bounds
        self.elapsed = 0.0
        self.shown_gold = 0.0     # the number currently displayed (counts up)
        self._gold = 0            # the real total from the latest stats
        self.coin_pop = 0.0       # seconds left of the coin's "pop"
        self._cards: dict[int, _Card] = {}
        self._labels: dict[str, arcade.Text] = {}
        self.icons, self.grey_icons = {}, {}
        for name in FOOD_NAMES:
            path = FOOD_DIR / f"{name}.png"
            if path.is_file():   # logic and layout still work with placeholder art
                self.icons[name] = arcade.load_texture(path)
                self.grey_icons[name] = greyscale_texture(self.icons[name])
        self.glow = arcade.make_soft_circle_texture(96, GOLD, center_alpha=150, outer_alpha=0)

    # ------------------------------------------------------------ animation
    def notify(self, event: OrderEvent) -> None:
        """Start the matching card animation for something OrderSystem reported."""
        card = self._cards.get(event.order_id)
        if event.kind in ("served", "expired") and card is not None:
            card.ghost, card.ghost_age, card.gold = event.kind, 0.0, event.gold
        if event.kind == "served":
            self.coin_pop = 0.35

    def reset(self) -> None:
        self._cards.clear()
        self.shown_gold = 0.0
        self._gold = 0
        self.coin_pop = 0.0

    def update(self, delta_time: float, orders: tuple[OrderSnapshot, ...] | None = None,
               stats: OrderStats | None = None) -> None:
        """Advance animations by game time. Passing the current snapshots and
        stats lets a new card slide in, and the gold count up, at once."""
        if orders is not None:
            self._sync(orders)
        if stats is not None:
            self._gold = stats.score
        self.elapsed += delta_time
        self.coin_pop = max(0.0, self.coin_pop - delta_time)
        # Count the displayed gold up towards the real total.
        self.shown_gold += (self._gold - self.shown_gold) * min(1.0, delta_time * 7)
        if abs(self._gold - self.shown_gold) < 0.6:
            self.shown_gold = float(self._gold)
        ease = min(1.0, delta_time * 10)
        for order_id, card in list(self._cards.items()):
            card.age += delta_time
            card.slide += (0 - card.slide) * ease
            if card.y is not None:
                card.y += (card.target_y - card.y) * ease
            if card.ghost:
                card.ghost_age += delta_time
                if card.ghost_age >= GHOST_SECONDS:
                    del self._cards[order_id]

    def _slot_y(self, index: int) -> float:
        top = self.bottom + self.height - GOLD_HEIGHT - CARD_GAP
        return top - (index + 1) * CARD_HEIGHT - index * CARD_GAP

    def _sync(self, orders) -> list[_Card]:
        """Match animation records to the current snapshots, oldest first.

        Safe to call any number of times per frame: it only creates, removes
        and re-targets cards; movement happens in update().
        """
        live = {order.order_id for order in orders}
        for order in orders:
            card = self._cards.get(order.order_id)
            if card is None:      # a new card enters from beyond the right edge
                card = self._cards[order.order_id] = _Card(self.width + 20.0)
            card.snapshot = order
        for order_id, card in list(self._cards.items()):
            if order_id not in live and not card.ghost:
                del self._cards[order_id]   # removed without an event (e.g. reset)
        # IDs only ever increase, so sorting by ID is oldest first. A finished
        # card keeps its slot while its banner shows; the rest close the gap after.
        ordered = sorted(self._cards.items())
        for index, (_, card) in enumerate(ordered):
            card.target_y = self._slot_y(index)
            if card.y is None:
                card.y = card.target_y
        return [card for _, card in ordered]

    # ------------------------------------------------------------ drawing
    def _text(self, text, key, value, x, y, size=12, color=INK, **kwargs):
        if text is not None:
            return text(key, value, x, y, size, color, **kwargs)
        label = self._labels.get(key)
        if label is None:
            label = self._labels[key] = arcade.Text(value, x, y, color, size, **kwargs)
        if label.text != value:
            label.text = value
        if (label.x, label.y) != (x, y):
            label.x, label.y = x, y
        if tuple(label.color)[:3] != tuple(color)[:3]:
            label.color = color
        label.draw()

    def draw(self, orders: tuple[OrderSnapshot, ...], stats: OrderStats, text=None,
             empty_message: str = "Waiting for customers...") -> None:
        """Draw the panel. `text` is an optional (key, value, x, y, size, color)
        drawing function; GameView passes its resize-aware one."""
        arcade.draw_lbwh_rectangle_filled(self.left, self.bottom, self.width, self.height, PANEL)
        self._draw_gold(stats, text)
        cards = self._sync(orders)
        if not cards:
            self._text(text, "orders_empty", empty_message, self.left + self.width / 2,
                       self._slot_y(0) + CARD_HEIGHT / 2, 12, MUTED, anchor_x="center")
        floor = self.bottom - 1
        for index, card in enumerate(cards):
            if card.y is not None and card.y >= floor:
                self._draw_card(index, card, text)

    def _draw_gold(self, stats: OrderStats, text):
        self._gold = stats.score      # update() counts shown_gold up towards this
        x, top = self.left + 10, self.bottom + self.height
        pop = 1.0 + 0.5 * (self.coin_pop / 0.35) if self.coin_pop else 1.0
        cx, cy = x + 16, top - 24
        if self.coin_pop:
            arcade.draw_texture_rect(self.glow, arcade.XYWH(cx, cy, 64 * pop, 64 * pop))
        arcade.draw_circle_filled(cx, cy, 13 * pop, GOLD_DARK)
        arcade.draw_circle_filled(cx, cy, 11 * pop, GOLD)
        arcade.draw_circle_filled(cx - 3 * pop, cy + 3 * pop, 3 * pop, (255, 238, 170))
        target = f" / {stats.target}" if stats.target else ""
        self._text(text, "gold_value", f"{int(round(self.shown_gold))}{target} G", x + 38, top - 32, 17, GOLD)
        right = self.left + self.width - 10
        self._text(text, "gold_served", f"served {stats.completed}", right, top - 19, 9, MUTED,
                   anchor_x="right")
        self._text(text, "gold_missed", f"missed {stats.expired}", right, top - 32, 9,
                   RED if stats.expired else MUTED, anchor_x="right")
        # Progress towards the day target.
        bar_w = self.width - 20
        arcade.draw_lbwh_rectangle_filled(x, top - 54, bar_w, 9, (20, 30, 36))
        if stats.target:
            fraction = min(1.0, self.shown_gold / stats.target)
            done = fraction >= 1.0
            color = GREEN if done and blink_on(self.elapsed, 3) else GOLD
            arcade.draw_lbwh_rectangle_filled(x, top - 54, bar_w * fraction, 9, color)
            arcade.draw_lbwh_rectangle_filled(x, top - 48, bar_w * fraction, 2, (255, 236, 160))
        arcade.draw_lbwh_rectangle_outline(x, top - 54, bar_w, 9, CARD_EDGE, 1)

    def _draw_card(self, index: int, card: _Card, text):
        order = card.snapshot
        key = f"card{index}_"
        x = self.left + 6 + card.slide
        y = card.y
        w, h = self.width - 12, CARD_HEIGHT
        fresh = card.age < NEW_SECONDS and not card.ghost
        expired, served = card.ghost == "expired", card.ghost == "served"
        if expired:                      # shake, then fall away
            x += sin(card.ghost_age * 60) * 4 * max(0.0, 1 - card.ghost_age * 2)
        if card.ghost and card.ghost_age > GHOST_SECONDS - 0.3:
            x += (card.ghost_age - (GHOST_SECONDS - 0.3)) / 0.3 * (self.width + 20)
        fraction = max(0.0, min(1.0, order.remaining_seconds / order.patience_seconds))
        urgent = not card.ghost and order.remaining_seconds <= LOW_TIME

        body, edge = CARD, CARD_EDGE
        if fresh:                        # a new order glows gold, then settles
            fade = 1.0 - card.age / NEW_SECONDS
            pulse = 0.5 + 0.5 * sin(self.elapsed * 6)
            arcade.draw_texture_rect(self.glow, arcade.XYWH(x + w / 2, y + h / 2, w * 1.25, h * 1.7),
                                     alpha=int((60 + 110 * pulse) * fade))
            edge = GOLD
        if served:
            body, edge = (40, 92, 70), GREEN
        elif expired:
            body, edge = (58, 58, 60), (110, 110, 112)
        elif urgent and blink_on(self.elapsed):
            body, edge = (96, 46, 44), RED
        arcade.draw_lbwh_rectangle_filled(x, y, w, h, edge)
        arcade.draw_lbwh_rectangle_filled(x + 2, y + 2, w - 4, h - 4, body)

        name_color = MUTED if expired else INK
        self._text(text, key + "id", f"#{order.order_id}", x + 9, y + h - 21, 11,
                   GOLD if not expired else MUTED, bold=True)
        self._text(text, key + "name", order.recipe_name, x + 36, y + h - 21, 12, name_color, bold=True)
        # Ingredient icons with quantities.
        icons = self.grey_icons if expired else self.icons
        ix = x + 10
        for ingredient, count in Counter(order.required).items():
            texture = icons.get(ingredient)
            if texture is not None:
                scale = 28 / max(texture.width, texture.height)
                draw_pixel_texture(texture, arcade.XYWH(ix + 14, y + 47, texture.width * scale,
                                                        texture.height * scale))
            else:
                grey = (130, 130, 130) if expired else FOOD_COLORS[ingredient]
                arcade.draw_lbwh_rectangle_filled(ix + 2, y + 35, 24, 24, grey)
            self._text(text, f"{key}{ingredient}_n", f"x{count}", ix + 30, y + 40, 11, name_color)
            ix += 56
        # Bottom row: status line or the timer.
        if served:
            self._text(text, key + "banner", f"SERVED  +{card.gold} G", x + w / 2, y + 11, 13, GREEN,
                       anchor_x="center", bold=True)
        elif expired:
            self._text(text, key + "banner", "EXPIRED", x + w / 2, y + 11, 13, RED,
                       anchor_x="center", bold=True)
        else:
            bar_w = w - 62
            arcade.draw_lbwh_rectangle_filled(x + 9, y + 10, bar_w, 8, (20, 30, 36))
            arcade.draw_lbwh_rectangle_filled(x + 9, y + 10, bar_w * fraction, 8, timer_color(fraction))
            seconds = max(0, ceil(order.remaining_seconds))   # 0.2 s shows as 1, never 0
            self._text(text, key + "timer", f"{seconds}s", x + w - 10, y + 8, 12,
                       RED if urgent else INK, anchor_x="right", bold=True)
        if not card.ghost:   # live value: the speed tip shrinks while the customer waits
            self._text(text, key + "reward", f"{order.reward} G", x + w - 10, y + h - 21, 11, GOLD,
                       anchor_x="right")
