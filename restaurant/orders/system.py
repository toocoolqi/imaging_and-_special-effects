"""Timed orders and progression for the shared restaurant game."""
from collections import Counter
from math import isfinite

from restaurant.shared.contracts import ActionResult, OrderSnapshot, OrderStats, ServeResult

RECIPES = (
    ("Tomato sandwich", ("sandwich", "tomato")),
    ("Creamy noodles", ("creamy_noodles",)),
)
GOLD_PER_ORDER = 100
DAY_GOAL = 200
ORDER_SECONDS = 60.0


class OrderSystem:
    """Own the current ticket. Serve only after consuming the checked plate."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._next_id = 1
        self._recipe_index = 0
        self.accepted = self.completed = self.expired = self.gold = 0
        self._pending_order()

    def _pending_order(self):
        self.order_id = self._next_id
        self._next_id += 1
        self.active = False
        self.remaining = ORDER_SECONDS

    def snapshot(self):
        name, required = RECIPES[self._recipe_index]
        return OrderSnapshot(self.order_id, name, required, self.remaining)

    def stats(self):
        return OrderStats(self.accepted, self.completed, self.expired, self.gold)

    def accept_next(self):
        if self.active:
            return ActionResult(False, "This order is already active.")
        self.active = True
        self.accepted += 1
        return ActionResult(True, "Order accepted.")

    def update(self, delta_time):
        if not isfinite(delta_time) or delta_time < 0:
            raise ValueError("Elapsed time must be finite and nonnegative.")
        if self.active:
            self.remaining = max(0, self.remaining - delta_time)
            if self.remaining == 0:
                self.expired += 1
                self._pending_order()
                return True
        return False

    def try_serve(self, plate, consume):
        order = self.snapshot()
        if not self.active:
            return ServeResult(False, "Accept an order at the hatch first.", None, plate.revision)
        if Counter(plate.ingredients) != Counter(order.required):
            return ServeResult(False, "That plate does not match the order.", order.order_id, plate.revision)
        if not consume(plate.revision):
            return ServeResult(False, "The plate changed. Try again.", order.order_id, plate.revision)
        self.completed += 1
        self.gold += GOLD_PER_ORDER
        self._recipe_index = (self._recipe_index + 1) % len(RECIPES)
        self._pending_order()
        return ServeResult(True, f"Order served. +{GOLD_PER_ORDER} gold.", order.order_id, plate.revision)
