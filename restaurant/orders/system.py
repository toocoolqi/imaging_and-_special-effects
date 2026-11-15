"""Timed orders and revision-checked serving, independent of Arcade."""
from collections import Counter
from dataclasses import dataclass, replace
from math import isfinite
from random import Random

from restaurant.ingredients.system import IngredientSystem, recipe_item
from restaurant.shared.contracts import ActionResult, FoodId, OrderSnapshot, OrderStats, PlateSnapshot, ServeResult

ORDER_SECONDS = 120.0
BONUS_SECONDS = 30.0
BONUS_SCORE = 50
MAX_ORDERS = 3
ORDER_ARRIVAL_RANGE = (5.0, 10.0)
HAND_SERVICE_ITEMS = ("sandwich", "milk")
SERVE_SCORE = 100


@dataclass(frozen=True)
class Recipe:
    name: str
    required: tuple[FoodId, ...]


RECIPES = (
    Recipe("Tomato sandwich", ("sandwich", "tomato")),
    Recipe("Pasta", ("pasta",)),
    Recipe("Sandwich", ("sandwich",)),
    Recipe("Milk", ("milk",)),
)


class OrderSystem:
    def __init__(self, seed: int | None = None):
        self._random = Random(seed)
        self.reset()

    def reset(self):
        self._orders: list[OrderSnapshot] = []
        self._next_id = 1
        self._accepted = self._completed = self._expired = 0
        self._score = 0
        self._until_arrival = self._random.uniform(*ORDER_ARRIVAL_RANGE)
        self.started = False

    def _queue_order(self):
        if len(self._orders) < MAX_ORDERS:
            recipe = RECIPES[(self._next_id - 1) % len(RECIPES)]
            self._orders.append(OrderSnapshot(self._next_id, recipe.name, recipe.required, ORDER_SECONDS, "accepted"))
            self._accepted += 1
            self._next_id += 1

    def snapshot(self) -> tuple[OrderSnapshot, ...]:
        return tuple(self._orders)

    def stats(self) -> OrderStats:
        return OrderStats(self._accepted, self._completed, self._expired, self._score)

    def start(self) -> ActionResult:
        if self.started:
            return ActionResult(False, "Service is already open")
        self.started = True
        self._queue_order()
        return ActionResult(True, "Service open. More orders are on the way")

    def update(self, dt: float) -> None:
        if not isfinite(dt) or dt < 0:
            raise ValueError("Order time must be finite and nonnegative")
        if not self.started:
            return
        while dt > 0:
            has_room = len(self._orders) < MAX_ORDERS
            until_expiry = min((order.remaining_seconds for order in self._orders), default=float("inf"))
            step = min(dt, until_expiry, self._until_arrival if has_room else float("inf"))
            survivors = []
            for order in self._orders:
                if order.remaining_seconds <= step:
                    self._expired += 1
                else:
                    survivors.append(replace(order, remaining_seconds=order.remaining_seconds - step))
            self._orders = survivors
            if has_room:
                self._until_arrival -= step
                if self._until_arrival <= 0:
                    self._queue_order()
                    self._until_arrival = self._random.uniform(*ORDER_ARRIVAL_RANGE)
            dt -= step

    def try_serve(self, plate: PlateSnapshot, food: IngredientSystem) -> ServeResult:
        revision = plate.revision
        if not self.started:
            return ServeResult(False, "Start service first", None, revision)
        if food.snapshot().plate != plate:
            return ServeResult(False, "Plate has changed", None, revision)
        if not plate.ingredients:
            return ServeResult(False, "Plate is empty", None, revision)
        contents = Counter(recipe_item(item) for item in plate.ingredients)
        order = next((order for order in self._orders
                      if Counter(recipe_item(item) for item in order.required) == contents), None)
        if order is None:
            return ServeResult(False, "Plate does not match an active order", None, revision)
        if not food.serve_plate(revision):
            return ServeResult(False, "Carry the matching plate to serve", None, revision)
        return self._complete(order, revision)

    def try_serve_held(self, food: IngredientSystem) -> ServeResult:
        state = food.snapshot()
        revision = state.plate.revision
        if not self.started:
            return ServeResult(False, "Start service first", None, revision)
        if state.held not in HAND_SERVICE_ITEMS:
            return ServeResult(False, "Only sandwich or milk can be served by hand", None, revision)
        order = next((order for order in self._orders if order.required == (state.held,)), None)
        if order is None:
            return ServeResult(False, "No active order for that item", None, revision)
        if not food.serve_held(state.held):
            return ServeResult(False, "Held item has changed", None, revision)
        return self._complete(order, revision)

    def _complete(self, order: OrderSnapshot, revision: int) -> ServeResult:
        self._orders.remove(order)
        self._completed += 1
        bonus = BONUS_SCORE if ORDER_SECONDS - order.remaining_seconds <= BONUS_SECONDS else 0
        self._score += SERVE_SCORE + bonus
        message = f"Served #{order.order_id}: {order.recipe_name} (+{SERVE_SCORE + bonus})"
        return ServeResult(True, message, order.order_id, revision)
