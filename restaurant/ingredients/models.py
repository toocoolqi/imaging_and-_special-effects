"""Private ingredient storage; public records live in shared.contracts."""
from dataclasses import dataclass, field
from typing import Final

from restaurant.shared.contracts import FoodId

PLATE_CAPACITY: Final = 4


@dataclass
class _IngredientState:
    """Owned exclusively by IngredientSystem, never returned to callers."""

    _held: FoodId | None = None
    _plate: list[FoodId] = field(default_factory=list)
    _revision: int = 0
    _carrying_plate: bool = False
