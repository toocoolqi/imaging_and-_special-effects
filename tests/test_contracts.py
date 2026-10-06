"""Shared snapshots stay immutable and interoperable without either system."""
from dataclasses import FrozenInstanceError

import pytest

from restaurant.shared.contracts import (
    ActionResult, IngredientSnapshot, OrderSnapshot, OrderStats,
    PlateSnapshot, ServeResult,
)


def test_members_can_exchange_an_immutable_plate():
    plate = PlateSnapshot(("bread", "cheese"), 2)
    state = IngredientSnapshot(None, plate)
    order = OrderSnapshot(1, "cheese toast", ("bread", "cheese"), 60.0)
    result = ServeResult(True, "Matched", order.order_id, state.plate.revision)
    assert result.plate_revision == 2
    with pytest.raises(FrozenInstanceError):
        plate.revision = 99
    with pytest.raises(TypeError):
        plate.ingredients[0] = "tomato"


@pytest.mark.parametrize("ingredients", [["bread"], ("unknown",)])
def test_plate_rejects_mutable_or_invalid_ingredients(ingredients):
    with pytest.raises(ValueError):
        PlateSnapshot(ingredients, 0)


def test_duplicate_ingredients_remain_valid_and_ordered():
    plate = PlateSnapshot(("bread", "bread", "cheese"), 3)
    assert plate.ingredients == ("bread", "bread", "cheese")


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
        OrderSnapshot(1, "salad", ("lettuce", "tomato"), float("nan"))
