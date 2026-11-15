"""Private ingredient storage; public records live in shared.contracts."""
from dataclasses import dataclass, field
from typing import Final

from restaurant.shared.contracts import DishId, FoodId, IngredientId, PlateLocation, PotSnapshot

PLATE_CAPACITY: Final = 4


@dataclass(frozen=True)
class PotRecipe:
    required: frozenset[IngredientId]
    duration: float
    dish: DishId


POT_RECIPE = PotRecipe(frozenset(("noodles", "milk", "tomato")), 4.0, "pasta")


@dataclass
class _IngredientState:
    """Owned exclusively by IngredientSystem, never returned to callers."""

    _held: FoodId | None = None
    _plate: list[FoodId] = field(default_factory=list)
    _revision: int = 0
    _location: PlateLocation = PlateLocation.DOCKED
    _pot: PotSnapshot = PotSnapshot()
