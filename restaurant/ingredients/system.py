"""Ingredient and plate actions, independent of rendering and player movement."""
from typing import get_args

from restaurant.ingredients.models import PLATE_CAPACITY, _IngredientState
from restaurant.shared.contracts import (
    ActionResult, IngredientId, IngredientSnapshot, PlateSnapshot,
)

_VALID_INGREDIENTS = get_args(IngredientId)


class IngredientSystem:
    """Own one held ingredient and one plate; expose immutable snapshots only."""

    def __init__(self) -> None:
        self._state = _IngredientState()

    def collect(self, ingredient_id: IngredientId) -> ActionResult:
        if ingredient_id not in _VALID_INGREDIENTS:
            raise ValueError(f"Unknown ingredient ID: {ingredient_id!r}")
        if self._state._held is not None or self._state._carrying_plate:
            return ActionResult(False, "Hand is full")
        self._state._held = ingredient_id
        return ActionResult(True, f"Collected {ingredient_id}")

    def add_to_plate(self) -> ActionResult:
        if self._state._carrying_plate:
            return ActionResult(False, "Return the plate to the island first")
        ingredient = self._state._held
        if ingredient is None:
            return ActionResult(False, "Hand is empty")
        if len(self._state._plate) >= PLATE_CAPACITY:
            return ActionResult(False, "Plate is full")
        self._state._plate.append(ingredient)
        self._state._held = None
        self._state._revision += 1
        return ActionResult(True, f"Added {ingredient}")

    def remove_from_plate(self) -> ActionResult:
        if self._state._carrying_plate:
            return ActionResult(False, "Return the plate to the island first")
        if self._state._held is not None:
            return ActionResult(False, "Hand is full")
        if not self._state._plate:
            return ActionResult(False, "Plate is empty")
        ingredient = self._state._plate.pop()
        self._state._held = ingredient
        self._state._revision += 1
        return ActionResult(True, f"Removed {ingredient}")

    def discard(self) -> ActionResult:
        if self._state._carrying_plate:
            return ActionResult(False, "Return the plate to the island first")
        if self._state._held is not None:
            ingredient = self._state._held
            self._state._held = None
            return ActionResult(True, f"Discarded {ingredient}")
        if self._state._plate:
            self._state._plate.clear()
            self._state._revision += 1
            return ActionResult(True, "Plate cleared")
        return ActionResult(False, "Nothing to discard")

    def snapshot(self) -> IngredientSnapshot:
        return IngredientSnapshot(
            self._state._held,
            PlateSnapshot(tuple(self._state._plate), self._state._revision),
            self._state._carrying_plate,
        )

    def clear_plate(self, expected_revision: int) -> bool:
        """Consume only the plate revision that the order system checked."""
        if expected_revision != self._state._revision:
            return False
        if self._state._plate:
            self._state._plate.clear()
            self._state._revision += 1
        return True

    def use_plate(self) -> ActionResult:
        if self._state._held is not None:
            return self.add_to_plate()
        if self._state._carrying_plate:
            self._state._carrying_plate = False
            self._state._revision += 1
            return ActionResult(True, "Plate returned to the island")
        if not self._state._plate:
            return ActionResult(False, "Plate is empty. Bring food from the pantry or pot.")
        self._state._carrying_plate = True
        self._state._revision += 1
        return ActionResult(True, "Plate picked up. Take it to the service hatch.")

    def take_held(self):
        item = self._state._held
        self._state._held = None
        return item

    def take_cooked_portion(self) -> ActionResult:
        if self._state._held is not None or self._state._carrying_plate:
            return ActionResult(False, "Your hands are full")
        self._state._held = "creamy_noodles"
        return ActionResult(True, "Collected creamy noodles")

    def reset(self) -> None:
        """Start a new session, including restarting the plate revision at zero."""
        self._state = _IngredientState()
