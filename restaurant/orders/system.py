"""Order rules: arrivals, timers, matching, gold and the day target.

Pure Python. The life of one order:

    arrives -> live at once, its timer starts   -> event "arrived"
        -> try_serve(matching plate) in time    -> event "served", gold paid
        -> timer reaches zero first             -> event "expired", no gold

Serving is one transaction with the food system. try_serve checks the plate
snapshot, then asks the food system to consume exactly that plate revision
(food.serve_plate), and only then changes orders or gold. If anything does
not match, nothing changes, so a repeated key press can never be paid twice.
"""
from collections import Counter
from math import isfinite
from random import Random

from restaurant.ingredients.system import recipe_item
from restaurant.orders.models import (
    HAND_SERVICE_ITEMS, RECIPE_BY_ID, DayRules, Recipe, _Order,
)
from restaurant.shared.contracts import (
    OrderEvent, OrderSnapshot, OrderStats, PlateSnapshot, ServeResult,
)

__all__ = ["HAND_SERVICE_ITEMS", "OrderSystem", "plate_matches"]

EMPTY_BOARD_GAP = 2.0   # seconds until the next customer when no orders are left


def plate_matches(required, items) -> bool:
    """Same foods in the same quantities; placement order is ignored.

    Counter keeps duplicates (a set would not), and recipe_item lets a
    chopped tomato fill a "tomato" slot.
    """
    return (Counter(recipe_item(item) for item in required)
            == Counter(recipe_item(item) for item in items))


class OrderSystem:
    def __init__(self, seed: int | None = None, rules: DayRules | None = None):
        self._seed = seed
        self._rules = rules or DayRules()
        self.reset(seed)

    # ------------------------------------------------------------ session
    def reset(self, seed: int | None = None, rules: DayRules | None = None) -> None:
        """Start a new day: IDs from 1, counters at 0, the first order arrives."""
        if rules is not None:
            self._rules = rules
        self._random = Random(self._seed if seed is None else seed)
        self._orders: list[_Order] = []
        self._next_id = 1
        self._accepted = self._completed = self._expired = self._gold = 0
        self._day_complete = False
        self._events: list[OrderEvent] = []
        self._until_arrival = self._next_gap()
        self._queue_order()

    @property
    def rules(self) -> DayRules:
        return self._rules

    @property
    def is_day_complete(self) -> bool:
        return self._day_complete

    @property
    def active_count(self) -> int:
        """Orders on the board, each with its timer running."""
        return len(self._orders)

    # ------------------------------------------------------------ time
    def update(self, dt: float) -> None:
        """Advance every order's timer. Large steps are split at each expiry
        and arrival, so the result is the same as many small frames."""
        if not isfinite(dt) or dt < 0:
            raise ValueError("Order time must be finite and nonnegative")
        while dt > 0 and not self._day_complete:
            has_room = len(self._orders) < self._rules.max_cards
            step = min(dt, min((o.remaining for o in self._orders), default=dt),
                       self._until_arrival if has_room else dt)
            for order in list(self._orders):
                order.remaining -= step
                if order.remaining <= 1e-9:
                    self._orders.remove(order)
                    self._expired += 1
                    self._events.append(OrderEvent("expired", order.order_id, order.recipe.name))
            if has_room:
                self._until_arrival -= step
                if self._until_arrival <= 1e-9:
                    self._queue_order()
                    self._until_arrival = self._next_gap()
            if not self._orders:          # an empty board gets a customer soon
                self._until_arrival = min(self._until_arrival, EMPTY_BOARD_GAP)
            dt -= step

    # ------------------------------------------------------------ actions
    def try_serve(self, plate: PlateSnapshot, food=None) -> ServeResult:
        """Serve the oldest order this plate satisfies.

        With `food` (the IngredientSystem), the exact plate revision is
        consumed through food.serve_plate before any order changes. Without
        it the call only checks and scores, and the caller must clear the
        plate (used by the independent orders demo).
        """
        if not isinstance(plate, PlateSnapshot):
            raise ValueError("try_serve needs a PlateSnapshot.")
        revision = plate.revision
        failure = self._serve_refusal(revision)
        if failure:
            return failure
        if food is not None and food.snapshot().plate != plate:
            return ServeResult(False, "Plate has changed", None, revision)
        if not plate.ingredients:
            return ServeResult(False, "The plate is empty", None, revision)
        order = next((o for o in self._orders
                      if plate_matches(o.recipe.required, plate.ingredients)), None)
        if order is None:
            return ServeResult(False, "No order wants this plate", None, revision)
        if food is not None and not food.serve_plate(revision):
            return ServeResult(False, "Carry the matching plate to serve", None, revision)
        return self._complete(order, revision)

    def try_serve_held(self, food) -> ServeResult:
        """Hand over a single sandwich or milk without using the plate."""
        state = food.snapshot()
        revision = state.plate.revision
        failure = self._serve_refusal(revision)
        if failure:
            return failure
        if state.held not in HAND_SERVICE_ITEMS:
            return ServeResult(False, "Only sandwich or milk can be served by hand", None, revision)
        order = next((o for o in self._orders if o.recipe.by_hand
                      and o.recipe.required == (state.held,)), None)
        if order is None:
            return ServeResult(False, f"No order wants {state.held}", None, revision)
        if not food.serve_held(state.held):
            return ServeResult(False, "Held item has changed", None, revision)
        return self._complete(order, revision)

    # ------------------------------------------------------------ reading
    def snapshot(self) -> tuple[OrderSnapshot, ...]:
        """Immutable cards, oldest first. Editing them cannot change the system."""
        patience = self._rules.patience_seconds
        return tuple(OrderSnapshot(o.order_id, o.recipe.name, o.recipe.required,
                                   max(0.0, o.remaining), o.status, patience, self._reward(o))
                     for o in self._orders)

    def stats(self) -> OrderStats:
        return OrderStats(self._accepted, self._completed, self._expired, self._gold,
                          self._rules.target_gold)

    def drain_events(self) -> tuple[OrderEvent, ...]:
        """Hand over what happened since the last call (for effects and sound)."""
        events, self._events = tuple(self._events), []
        return events

    # ------------------------------------------------------------ private
    def _serve_refusal(self, revision):
        if self._day_complete:
            return ServeResult(False, "The day is complete", None, revision)
        if not self._orders:
            return ServeResult(False, "No orders right now", None, revision)
        return None

    def _complete(self, order: _Order, revision: int) -> ServeResult:
        gold = self._reward(order)
        self._orders.remove(order)
        self._completed += 1
        self._gold += gold
        self._events.append(OrderEvent("served", order.order_id, order.recipe.name, gold))
        if self._gold >= self._rules.target_gold:
            self._day_complete = True
            self._events.append(OrderEvent("day_complete", gold=self._gold))
        elif not self._orders:
            self._until_arrival = min(self._until_arrival, EMPTY_BOARD_GAP)
        return ServeResult(True, f"Served #{order.order_id}: {order.recipe.name} (+{gold} gold)",
                           order.order_id, revision, gold)

    def _reward(self, order: _Order) -> int:
        """Base price plus a speed tip that shrinks while the customer waits."""
        fraction = max(0.0, min(1.0, order.remaining / self._rules.patience_seconds))
        return order.recipe.base_gold + int(self._rules.tip_max * fraction)

    def _next_gap(self) -> float:
        average = self._rules.arrival_seconds
        return self._random.uniform(average * 0.75, average * 1.25)

    def _queue_order(self) -> None:
        if len(self._orders) >= self._rules.max_cards:
            return
        on_board = {order.recipe.recipe_id for order in self._orders}
        choices = [rid for rid in self._rules.recipe_ids if rid not in on_board]
        recipe: Recipe = RECIPE_BY_ID[self._random.choice(choices or list(self._rules.recipe_ids))]
        # Live at once: the timer starts the moment the order appears.
        order = _Order(self._next_id, recipe, "accepted", self._rules.patience_seconds)
        self._next_id += 1
        self._accepted += 1
        self._orders.append(order)
        self._events.append(OrderEvent("arrived", order.order_id, recipe.name))
