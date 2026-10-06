"""Immutable records agreed by all three members; no system logic lives here."""
from dataclasses import dataclass
from math import isfinite
from typing import Literal

Direction = Literal["up", "down", "left", "right"]
IngredientId = Literal["lettuce", "tomato", "bread", "cheese"]
TargetKind = Literal["box", "plate", "bin", "serve"]


@dataclass(frozen=True)
class InteractionTarget:
    """A reachable point on the FLOOR beside an object, not its solid center."""
    target_id: str
    kind: TargetKind
    x: float
    y: float
    ingredient_id: IngredientId | None = None

    def __post_init__(self):
        if not self.target_id or self.kind not in ("box", "plate", "bin", "serve"):
            raise ValueError("Target needs a nonempty ID and a valid kind.")
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("Target coordinates must be finite.")
        if self.kind == "box":
            if self.ingredient_id not in ("lettuce", "tomato", "bread", "cheese"):
                raise ValueError("A box must identify its ingredient.")
        elif self.ingredient_id is not None:
            raise ValueError("Only box targets have an ingredient ID.")


def _validate_ingredients(values):
    if not isinstance(values, tuple):
        raise ValueError("Ingredient collections must be immutable tuples.")
    if any(value not in ("lettuce", "tomato", "bread", "cheese") for value in values):
        raise ValueError("Unknown ingredient ID.")


def _nonnegative_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer.")


@dataclass(frozen=True)
class PlateSnapshot:
    ingredients: tuple[IngredientId, ...]
    revision: int

    def __post_init__(self):
        _validate_ingredients(self.ingredients)
        _nonnegative_integer(self.revision, "revision")


@dataclass(frozen=True)
class IngredientSnapshot:
    held: IngredientId | None
    plate: PlateSnapshot

    def __post_init__(self):
        if self.held is not None:
            _validate_ingredients((self.held,))
        if not isinstance(self.plate, PlateSnapshot):
            raise ValueError("plate must be a PlateSnapshot.")


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str


@dataclass(frozen=True)
class OrderSnapshot:
    order_id: int
    recipe_name: str
    required: tuple[IngredientId, ...]
    remaining_seconds: float

    def __post_init__(self):
        _nonnegative_integer(self.order_id, "order_id")
        _validate_ingredients(self.required)
        if not isfinite(self.remaining_seconds):
            raise ValueError("remaining_seconds must be finite.")


@dataclass(frozen=True)
class OrderStats:
    accepted: int
    completed: int
    expired: int
    score: int

    def __post_init__(self):
        for name in ("accepted", "completed", "expired", "score"):
            _nonnegative_integer(getattr(self, name), name)


@dataclass(frozen=True)
class ServeResult:
    success: bool
    message: str
    order_id: int | None
    plate_revision: int

    def __post_init__(self):
        _nonnegative_integer(self.plate_revision, "plate_revision")
        if self.order_id is not None:
            _nonnegative_integer(self.order_id, "order_id")
