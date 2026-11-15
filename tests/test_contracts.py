"""Shared snapshots stay immutable and interoperable without either system."""
from dataclasses import FrozenInstanceError

import pytest

from restaurant.shared.contracts import (
    ActionResult, IngredientSnapshot, OrderEvent, OrderSnapshot, OrderStats,
    PlateSnapshot, ServeResult,
)


def test_members_can_exchange_an_immutable_plate():
    plate = PlateSnapshot(("noodles", "milk"), 2)
    state = IngredientSnapshot(None, plate)
    order = OrderSnapshot(1, "Sample meal", ("noodles", "milk"), 60.0)
    result = ServeResult(True, "Matched", order.order_id, state.plate.revision)
    assert result.plate_revision == 2
    with pytest.raises(FrozenInstanceError):
        plate.revision = 99
    with pytest.raises(TypeError):
        plate.ingredients[0] = "tomato"


@pytest.mark.parametrize("ingredients", [["noodles"], ("unknown",)])
def test_plate_rejects_mutable_or_invalid_ingredients(ingredients):
    with pytest.raises(ValueError):
        PlateSnapshot(ingredients, 0)


def test_duplicate_ingredients_remain_valid_and_ordered():
    plate = PlateSnapshot(("noodles", "noodles", "milk"), 3)
    assert plate.ingredients == ("noodles", "noodles", "milk")


def test_invalid_revisions_and_stats_are_rejected():
    with pytest.raises(ValueError):
        PlateSnapshot((), -1)
    with pytest.raises(ValueError):
        ServeResult(False, "Failed", None, -1)
    with pytest.raises(ValueError):
        OrderStats(3, 0, 0, -1)


def test_normal_failure_and_empty_state_are_valid():
    assert not ActionResult(False, "Hand full").success
    assert IngredientSnapshot(None, PlateSnapshot((), 0)).held is None
    assert OrderStats(3, 0, 0, 0).accepted == 3
    assert ServeResult(False, "No match", None, 0).order_id is None


def test_invalid_held_ingredient_or_timer_is_rejected():
    with pytest.raises(ValueError):
        IngredientSnapshot("unknown", PlateSnapshot((), 0))
    with pytest.raises(ValueError):
        OrderSnapshot(1, "salad", ("sandwich", "tomato"), float("nan"))


def test_new_order_fields_have_safe_defaults_for_existing_callers():
    order = OrderSnapshot(1, "Sample meal", ("noodles", "milk"), 60.0)
    assert (order.status, order.patience_seconds, order.reward) == ("pending", 120.0, 0)
    assert OrderStats(3, 0, 0, 0).target == 0
    assert ServeResult(True, "Matched", 1, 2).gold == 0


def test_order_reward_gold_and_events_are_validated():
    ticket = OrderSnapshot(2, "Pasta", ("pasta",), 90.0, "accepted", 90.0, 120)
    assert ticket.reward == 120 and ticket.patience_seconds == 90.0
    with pytest.raises(ValueError):
        OrderSnapshot(2, "Pasta", ("pasta",), 90.0, "accepted", 0.0)
    with pytest.raises(ValueError):
        OrderSnapshot(2, "Pasta", ("pasta",), 90.0, "accepted", 90.0, -5)
    with pytest.raises(ValueError):
        ServeResult(False, "No match", None, 0, 50)        # a failure can never pay
    with pytest.raises(ValueError):
        OrderStats(1, 0, 0, 0, -1)
    event = OrderEvent("served", 4, "Pasta", 67)
    assert (event.kind, event.gold) == ("served", 67)
    assert OrderEvent("day_complete", gold=210).order_id is None
    with pytest.raises(ValueError):
        OrderEvent("exploded", 1)
