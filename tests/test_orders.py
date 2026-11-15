"""Order rules, tested without Arcade or a window.

Orders are live from the moment they arrive: their timer starts at once.

Run: python -m pytest tests/test_orders.py -q
"""
from dataclasses import FrozenInstanceError
import sys

import pytest

from restaurant.ingredients import IngredientSystem
from restaurant.orders import HAND_SERVICE_ITEMS, RECIPES, DayRules, OrderSystem, Recipe, plate_matches
from restaurant.shared.contracts import OrderEvent, OrderSnapshot, PlateLocation, PlateSnapshot

RULES = DayRules(target_gold=10_000)       # a day that never ends by accident
PLATE_RECIPES = DayRules(target_gold=10_000, recipe_ids=("tomato_sandwich", "lunch_set", "pasta"))


def plate(*items, revision=1):
    return PlateSnapshot(tuple(items), revision)


def full_board(seed=5, rules=RULES):
    """Three live orders."""
    system = OrderSystem(seed, rules)
    while len(system.snapshot()) < rules.max_cards:
        system.update(rules.arrival_seconds * 1.3)
    system.drain_events()
    return system


def test_order_logic_needs_no_graphics_library():
    assert not hasattr(sys.modules["restaurant.orders.system"], "arcade")
    assert not hasattr(sys.modules["restaurant.orders.models"], "arcade")


# ---------------------------------------------------------------- arrival

def test_new_day_starts_with_one_live_order_and_zero_counters():
    system = OrderSystem(seed=1)
    (order,) = system.snapshot()
    assert order.order_id == 1 and order.status == "accepted"
    assert order.remaining_seconds == order.patience_seconds == system.rules.patience_seconds
    stats = system.stats()
    assert (stats.accepted, stats.completed, stats.expired, stats.score) == (1, 0, 0, 0)
    assert stats.target == system.rules.target_gold
    assert system.drain_events() == (OrderEvent("arrived", 1, order.recipe_name),)
    assert system.drain_events() == ()


def test_the_timer_starts_the_moment_an_order_arrives():
    system = OrderSystem(seed=2, rules=RULES)
    system.update(5.0)
    assert system.snapshot()[0].remaining_seconds == pytest.approx(RULES.patience_seconds - 5.0)
    system.update(RULES.arrival_seconds * 1.3)       # a second order arrives mid-step
    first, second = system.snapshot()[:2]
    assert second.remaining_seconds > first.remaining_seconds
    assert second.remaining_seconds < RULES.patience_seconds   # already ticking


def test_customers_arrive_over_time_but_never_more_than_three():
    system = OrderSystem(seed=3, rules=DayRules(target_gold=10_000, patience_seconds=500.0))
    for _ in range(40):
        system.update(RULES.arrival_seconds)
        assert len(system.snapshot()) <= RULES.max_cards
    cards = system.snapshot()
    assert len(cards) == RULES.max_cards
    assert [card.order_id for card in cards] == sorted(card.order_id for card in cards)


def test_same_seed_gives_the_same_sequence_and_different_seeds_differ():
    def names(seed):
        system = OrderSystem(seed, PLATE_RECIPES)
        seen = []
        for _ in range(12):
            system.update(2.0)                     # let the next customer in
            top = system.snapshot()[0]
            seen.append(top.recipe_name)
            assert system.try_serve(plate(*top.required)).success
        return seen
    assert names(7) == names(7)
    assert any(names(7) != names(seed) for seed in (8, 9, 10, 11))


def test_menu_is_valid_and_recipes_reject_bad_data():
    assert len({recipe.recipe_id for recipe in RECIPES}) == len(RECIPES)
    assert {"pasta", "tomato_sandwich"} <= {recipe.recipe_id for recipe in RECIPES}
    assert set(HAND_SERVICE_ITEMS) == {"sandwich", "milk"}
    with pytest.raises(ValueError):
        Recipe("bad", "Bad", ("cheese",), 10)
    with pytest.raises(ValueError):
        Recipe("big", "Big", ("milk",) * 5, 10)
    with pytest.raises(ValueError):
        Recipe("two", "Two by hand", ("milk", "sandwich"), 10, by_hand=True)
    with pytest.raises(ValueError):
        DayRules(recipe_ids=("unknown",))
    with pytest.raises(ValueError):
        DayRules(patience_seconds=0)


# ---------------------------------------------------------------- matching

@pytest.mark.parametrize("required, given, expected", [
    (("sandwich", "tomato"), ("tomato", "sandwich"), True),                  # reordered
    (("sandwich", "tomato"), ("sandwich", "chopped_tomato"), True),          # chopped counts
    (("noodles", "noodles", "milk"), ("noodles", "milk"), False),            # wrong count
    (("sandwich", "milk"), ("sandwich", "milk", "milk"), False),             # duplicate extra
    (("sandwich", "tomato"), ("sandwich",), False),                         # missing
    (("pasta",), ("noodles", "milk", "tomato"), False),                      # raw is not cooked
    (("sandwich", "tomato"), (), False),                                    # empty
])
def test_matching_compares_quantities_not_sets_or_order(required, given, expected):
    assert plate_matches(required, given) is expected


# ---------------------------------------------------------------- serving

def test_an_empty_plate_changes_nothing():
    system = OrderSystem(seed=4, rules=PLATE_RECIPES)
    system.drain_events()
    before = (system.snapshot(), system.stats())
    result = system.try_serve(plate(revision=2))
    assert not result.success and result.plate_revision == 2 and result.order_id is None
    assert (system.snapshot(), system.stats()) == before
    assert system.drain_events() == ()


@pytest.mark.parametrize("wrong", ["missing", "extra", "duplicate", "other"])
def test_wrong_plate_changes_nothing(wrong):
    system = OrderSystem(seed=6, rules=DayRules(target_gold=10_000, recipe_ids=("tomato_sandwich",)))
    system.drain_events()
    required = system.snapshot()[0].required
    given = {"missing": ("sandwich",), "extra": required + ("milk",),
             "duplicate": required + ("sandwich",), "other": ("noodles", "milk")}[wrong]
    before = (system.snapshot(), system.stats())
    result = system.try_serve(plate(*given, revision=9))
    assert not result.success and result.order_id is None
    assert result.plate_revision == 9 and result.gold == 0
    assert (system.snapshot(), system.stats()) == before
    assert system.drain_events() == ()


def test_correct_plate_in_any_order_completes_once_and_pays_gold():
    system = OrderSystem(seed=6, rules=PLATE_RECIPES)
    top = system.snapshot()[0]
    result = system.try_serve(plate(*reversed(top.required), revision=4))
    assert result.success and result.order_id == top.order_id
    assert result.plate_revision == 4 and result.gold == top.reward > 0
    assert system.stats().completed == 1 and system.stats().score == result.gold
    assert top.order_id not in {card.order_id for card in system.snapshot()}
    repeat = system.try_serve(plate(*top.required, revision=4))
    assert not repeat.success and system.stats().score == result.gold   # nobody else waiting
    system.update(2.0)
    assert system.snapshot(), "the next customer arrives within two seconds"


def test_serving_through_the_food_system_consumes_exactly_that_plate():
    food = IngredientSystem()
    system = OrderSystem(seed=1, rules=DayRules(target_gold=10_000, recipe_ids=("lunch_set",)))
    food.pickup_plate()
    food.collect("milk")
    food.collect("sandwich")
    stale = food.snapshot().plate
    food.return_plate()
    food.pickup_plate()                        # same food, newer revision
    assert not system.try_serve(stale, food).success
    current = food.snapshot().plate
    result = system.try_serve(current, food)
    assert result.success and result.plate_revision == current.revision
    after = food.snapshot().plate
    assert after.ingredients == () and after.location is PlateLocation.CARRIED   # chef keeps it
    assert not system.try_serve(current, food).success


def test_sandwich_and_milk_can_be_handed_over_without_the_plate():
    food = IngredientSystem()
    system = OrderSystem(seed=2, rules=DayRules(target_gold=10_000, recipe_ids=("sandwich", "milk")))
    wanted = system.snapshot()[0].required[0]
    other = "milk" if wanted == "sandwich" else "sandwich"
    food.collect(other)
    assert not system.try_serve_held(food).success
    assert food.snapshot().held == other
    food.discard()
    food.collect("tomato")
    assert not system.try_serve_held(food).success
    food.discard()
    food.collect(wanted)
    result = system.try_serve_held(food)
    assert result.success and result.gold > 0
    assert food.snapshot().held is None


def test_serving_picks_the_oldest_order_that_matches():
    system = full_board(rules=PLATE_RECIPES)
    cards = system.snapshot()
    target = cards[1]
    result = system.try_serve(plate(*target.required))
    assert result.order_id == target.order_id
    assert [card.order_id for card in system.snapshot()] == [cards[0].order_id, cards[2].order_id]


def test_faster_delivery_pays_a_bigger_tip():
    rules = DayRules(target_gold=10_000, patience_seconds=60.0, tip_max=30, recipe_ids=("pasta",))
    fast, slow = OrderSystem(11, rules), OrderSystem(11, rules)
    fast.update(1.0)
    slow.update(50.0)
    quick = fast.try_serve(plate("pasta")).gold
    late = slow.try_serve(plate("pasta")).gold
    assert 90 <= late < quick <= 120


# ---------------------------------------------------------------- timers

def test_zero_time_changes_nothing_and_bad_time_is_rejected():
    system = full_board()
    before = (system.snapshot(), system.stats())
    system.update(0)
    assert (system.snapshot(), system.stats()) == before
    for bad in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            system.update(bad)
    assert (system.snapshot(), system.stats()) == before


def test_order_expires_at_exactly_zero_and_cannot_be_served_afterwards():
    system = OrderSystem(seed=8, rules=DayRules(target_gold=10_000, arrival_seconds=500.0,
                                                recipe_ids=("tomato_sandwich",)))
    top = system.snapshot()[0]
    system.drain_events()
    system.update(system.rules.patience_seconds)
    assert top.order_id not in {card.order_id for card in system.snapshot()}
    stats = system.stats()
    assert (stats.expired, stats.completed, stats.score) == (1, 0, 0)
    assert OrderEvent("expired", top.order_id, top.recipe_name) in system.drain_events()
    assert not system.try_serve(plate(*top.required)).success   # too late
    system.update(2.0)
    fresh = system.snapshot()[0]                   # the next customer, soon after
    assert fresh.order_id != top.order_id and system.stats().score == 0


def test_one_big_step_matches_many_small_frames():
    big, small = full_board(seed=9), full_board(seed=9)
    big.update(300.0)
    for _ in range(3000):
        small.update(0.1)
    assert big.stats() == small.stats()
    assert [o.order_id for o in big.snapshot()] == [o.order_id for o in small.snapshot()]
    assert big.stats().expired > 3


def test_arrived_always_equals_completed_plus_expired_plus_on_the_board():
    system = OrderSystem(seed=10, rules=PLATE_RECIPES)
    for step in range(200):
        cards = system.snapshot()
        if cards and step % 4 == 0:
            system.try_serve(plate(*cards[0].required))
        system.update(13.0)
        stats = system.stats()
        assert stats.accepted == stats.completed + stats.expired + system.active_count
        assert len(system.snapshot()) <= RULES.max_cards
    assert stats.completed > 0 and stats.expired > 0


# ---------------------------------------------------------------- day target

def test_reaching_the_gold_target_completes_the_day_and_freezes_orders():
    system = OrderSystem(seed=12, rules=DayRules(target_gold=150, recipe_ids=("pasta",)))
    while not system.is_day_complete:
        system.update(2.0)
        assert system.try_serve(plate("pasta")).success
    events = system.drain_events()
    assert events.count(OrderEvent("day_complete", gold=system.stats().score)) == 1
    assert system.stats().score >= 150
    before = (system.snapshot(), system.stats())
    system.update(500.0)
    assert not system.try_serve(plate("pasta")).success
    assert (system.snapshot(), system.stats()) == before


# ---------------------------------------------------------------- safety

def test_snapshots_are_immutable_copies():
    system = full_board()
    cards = system.snapshot()
    with pytest.raises(FrozenInstanceError):
        cards[0].remaining_seconds = 999.0
    assert isinstance(cards, tuple) and isinstance(cards[0], OrderSnapshot)
    system.update(1.0)
    assert cards[0].remaining_seconds != system.snapshot()[0].remaining_seconds


def test_try_serve_rejects_anything_that_is_not_a_plate_snapshot():
    with pytest.raises(ValueError):
        OrderSystem(seed=1).try_serve(("sandwich", "tomato"))


def test_reset_restores_a_fresh_day_and_can_change_the_rules():
    system = full_board()
    system.try_serve(plate(*system.snapshot()[0].required))
    system.reset(seed=5)
    (order,) = system.snapshot()
    stats = system.stats()
    assert order.order_id == 1 and order.remaining_seconds == system.rules.patience_seconds
    assert (stats.accepted, stats.completed, stats.expired, stats.score) == (1, 0, 0, 0)
    system.reset(seed=5, rules=DayRules(target_gold=77, patience_seconds=30.0))
    assert system.stats().target == 77 and system.snapshot()[0].patience_seconds == 30.0
