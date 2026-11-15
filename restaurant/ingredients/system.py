"""Ingredient and plate actions, independent of rendering and player movement."""
from dataclasses import replace
from math import isfinite
from typing import get_args

from restaurant.ingredients.models import PLATE_CAPACITY, POT_RECIPE, _IngredientState
from restaurant.shared.contracts import (
    ActionResult, FoodId, IngredientId, IngredientSnapshot, PlateLocation, PlateSnapshot,
    PotSnapshot, PotStage,
)

_VALID_INGREDIENTS = get_args(IngredientId)


def recipe_item(food: FoodId) -> FoodId:
    """Preserve prepared food in inventory while matching its recipe role."""
    return "tomato" if food == "chopped_tomato" else food


class IngredientSystem:
    """Own one held ingredient and one plate; expose immutable snapshots only."""

    def __init__(self) -> None:
        self._state = _IngredientState()

    def collect(self, ingredient_id: IngredientId) -> ActionResult:
        if ingredient_id not in _VALID_INGREDIENTS:
            raise ValueError(f"Unknown ingredient ID: {ingredient_id!r}")
        if self._state._location is PlateLocation.CARRIED:
            return self._append_to_plate(ingredient_id)
        if self._state._held is not None:
            return ActionResult(False, "Hand is full")
        self._state._held = ingredient_id
        return ActionResult(True, f"Collected {ingredient_id}")

    def add_to_plate(self) -> ActionResult:
        if self._state._location is not PlateLocation.DOCKED:
            return ActionResult(False, "The plate must be on its table")
        ingredient = self._state._held
        if ingredient is None:
            return ActionResult(False, "Hand is empty")
        result = self._append_to_plate(ingredient)
        if result.success:
            self._state._held = None
        return result

    def _append_to_plate(self, food: FoodId) -> ActionResult:
        if food == POT_RECIPE.dish and self._state._plate:
            return ActionResult(False, "Pasta needs an empty plate")
        if POT_RECIPE.dish in self._state._plate:
            return ActionResult(False, "Pasta fills the plate")
        if len(self._state._plate) >= PLATE_CAPACITY:
            return ActionResult(False, "Plate is full")
        self._state._plate.append(food)
        self._state._revision += 1
        return ActionResult(True, f"Added {food.replace('_', ' ')}")

    def remove_from_plate(self) -> ActionResult:
        if self._state._location is not PlateLocation.DOCKED:
            return ActionResult(False, "Return the plate to remove food")
        if self._state._held is not None:
            return ActionResult(False, "Hand is full")
        if not self._state._plate:
            return ActionResult(False, "Plate is empty")
        ingredient = self._state._plate.pop()
        self._state._held = ingredient
        self._state._revision += 1
        return ActionResult(True, f"Removed {ingredient}")

    def discard(self) -> ActionResult:
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
            PlateSnapshot(tuple(self._state._plate), self._state._revision, self._state._location),
            self._state._pot,
        )

    def pickup_plate(self) -> ActionResult:
        state = self._state
        if state._held is not None:
            return ActionResult(False, "Hand is full")
        if state._location is not PlateLocation.DOCKED:
            return ActionResult(False, "Plate is away from the table")
        state._location = PlateLocation.CARRIED
        state._revision += 1
        return ActionResult(True, "Picked up plate")

    def return_plate(self) -> ActionResult:
        if self._state._location is not PlateLocation.CARRIED:
            return ActionResult(False, "You are not carrying the plate")
        self._state._location = PlateLocation.DOCKED
        self._state._revision += 1
        return ActionResult(True, "Returned plate to its table")

    def take_tomato_for_chopping(self) -> bool:
        state = self._state
        if state._location is PlateLocation.CARRIED and "tomato" in state._plate:
            state._plate.remove("tomato")
            state._revision += 1
            return True
        if state._held == "tomato":
            state._held = None
            return True
        return False

    def take_chopped_tomato(self) -> ActionResult:
        state = self._state
        if state._location is PlateLocation.CARRIED:
            return self._append_to_plate("chopped_tomato")
        if state._held is not None:
            return ActionResult(False, "Hand is full")
        state._held = "chopped_tomato"
        return ActionResult(True, "Picked up chopped tomato")

    def add_to_pot(self) -> ActionResult:
        state = self._state
        pot = state._pot
        if pot.stage not in (PotStage.EMPTY, PotStage.LOADING):
            return ActionResult(False, "Pot is cooking" if pot.stage is PotStage.COOKING else "Take the cooked portion first")
        carried = state._location is PlateLocation.CARRIED
        if carried:
            needed = POT_RECIPE.required.difference(pot.ingredients)
            # Remember the actual plate items so that a prepared tomato is
            # removed correctly and its raw equivalent fills the recipe slot.
            selected = {}
            for item in state._plate:
                ingredient = recipe_item(item)
                if ingredient in needed:
                    selected.setdefault(ingredient, item)
            if not selected:
                missing = " and ".join(sorted(needed))
                return ActionResult(False, f"Add {missing} to the plate first")
            added = tuple(selected)
        else:
            if state._held is None:
                return ActionResult(False, "Bring noodles, milk, and tomato to the pot")
            ingredient = recipe_item(state._held)
            if ingredient not in POT_RECIPE.required:
                return ActionResult(False, "The pot takes noodles, milk, and tomato")
            if ingredient in pot.ingredients:
                return ActionResult(False, "That ingredient is already in the pot")
            added = (ingredient,)
        loaded = (*pot.ingredients, *added)
        complete = POT_RECIPE.required == frozenset(loaded)
        state._pot = PotSnapshot(PotStage.COOKING if complete else PotStage.LOADING,
                                 loaded, POT_RECIPE.duration if complete else 0.0)
        if carried:
            for item in selected.values():
                state._plate.remove(item)
            state._revision += 1
        else:
            state._held = None
        return ActionResult(True, "Cooking pasta" if complete else f"Added {added[0]} to pot")

    def update(self, dt: float) -> None:
        if not isfinite(dt) or dt < 0:
            raise ValueError("Cooking time must be finite and nonnegative")
        pot = self._state._pot
        if pot.stage is PotStage.COOKING:
            remaining = max(0.0, pot.remaining_seconds - dt)
            self._state._pot = replace(pot, remaining_seconds=remaining,
                                       stage=PotStage.COOKING if remaining else PotStage.READY)

    def take_cooked_portion(self) -> ActionResult:
        state = self._state
        if state._pot.stage is not PotStage.READY:
            return ActionResult(False, "The pot is not ready")
        if state._location is not PlateLocation.CARRIED:
            return ActionResult(False, "Bring an empty plate to collect pasta")
        result = self._append_to_plate(POT_RECIPE.dish)
        if result.success:
            state._pot = PotSnapshot()
        return result

    def serve_plate(self, expected_revision: int) -> bool:
        state = self._state
        if (state._location is not PlateLocation.CARRIED
                or state._revision != expected_revision or not state._plate):
            return False
        state._location = PlateLocation.AT_SERVICE
        self.clear_plate(expected_revision)
        state._location = PlateLocation.CARRIED
        return True

    def serve_held(self, expected_food: FoodId) -> bool:
        if self._state._held != expected_food:
            return False
        self._state._held = None
        return True

    def clear_plate(self, expected_revision: int) -> bool:
        """Consume only the plate revision that the order system checked."""
        if expected_revision != self._state._revision:
            return False
        if self._state._plate:
            self._state._plate.clear()
            self._state._revision += 1
        return True

    def reset(self) -> None:
        """Start a new session, including restarting the plate revision at zero."""
        self._state = _IngredientState()
