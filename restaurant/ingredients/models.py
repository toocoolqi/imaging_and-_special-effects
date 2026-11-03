"""Private ingredient storage; public records live in shared.contracts."""
from dataclasses import dataclass, field
from typing import Final

from restaurant.shared.contracts import IngredientId

PLATE_CAPACITY: Final = 4


@dataclass
class _IngredientState:
    """Owned exclusively by IngredientSystem, never returned to callers."""

    _held: IngredientId | None = None
    _plate: list[IngredientId] = field(default_factory=list)
    _revision: int = 0
