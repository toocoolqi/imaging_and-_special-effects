"""Immutable records agreed by all three members; no system logic lives here."""
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Literal, get_args

Direction = Literal["up", "down", "left", "right"]
IngredientId = Literal["sandwich", "tomato", "noodles", "milk"]
DishId = Literal["pasta"]
PreparedFoodId = Literal["chopped_tomato"]
FoodId = IngredientId | PreparedFoodId | DishId
TargetKind = Literal["box", "plate", "bin", "serve", "chop", "pot"]
_RAW_IDS = get_args(IngredientId)
_FOOD_IDS = _RAW_IDS + get_args(PreparedFoodId) + get_args(DishId)


class PlateLocation(StrEnum):
    DOCKED = "docked"
    CARRIED = "carried"
    AT_SERVICE = "at_service"


class PotStage(StrEnum):
    EMPTY = "empty"
    LOADING = "loading"
    COOKING = "cooking"
    READY = "ready"


@dataclass(frozen=True)
class InteractionTarget:
    """A reachable point on the FLOOR beside an object, not its solid center."""
    target_id: str
    kind: TargetKind
    x: float
    y: float
    ingredient_id: IngredientId | None = None

    def __post_init__(self):
        if not self.target_id or self.kind not in ("box", "plate", "bin", "serve", "chop", "pot"):
            raise ValueError("Target needs a nonempty ID and a valid kind.")
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("Target coordinates must be finite.")
        if self.kind == "box":
            if self.ingredient_id not in _RAW_IDS:
                raise ValueError("A box must identify its ingredient.")
        elif self.ingredient_id is not None:
            raise ValueError("Only box targets have an ingredient ID.")


def _validate_food(values):
    if not isinstance(values, tuple):
        raise ValueError("Ingredient collections must be immutable tuples.")
    if any(value not in _FOOD_IDS for value in values):
        raise ValueError("Unknown food ID.")


def _nonnegative_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer.")


@dataclass(frozen=True)
class PlateSnapshot:
    ingredients: tuple[FoodId, ...]
    revision: int
    location: PlateLocation = PlateLocation.DOCKED

    def __post_init__(self):
        _validate_food(self.ingredients)
        _nonnegative_integer(self.revision, "revision")
        if not isinstance(self.location, PlateLocation):
            raise ValueError("Invalid plate location.")


@dataclass(frozen=True)
class PotSnapshot:
    stage: PotStage = PotStage.EMPTY
    ingredients: tuple[IngredientId, ...] = ()
    remaining_seconds: float = 0.0

    def __post_init__(self):
        if not isinstance(self.stage, PotStage):
            raise ValueError("Invalid pot stage.")
        if not isinstance(self.ingredients, tuple) or any(item not in _RAW_IDS for item in self.ingredients):
            raise ValueError("Pot ingredients must be an immutable tuple of raw food IDs.")
        if not isfinite(self.remaining_seconds) or self.remaining_seconds < 0:
            raise ValueError("Pot time must be finite and nonnegative.")


@dataclass(frozen=True)
class IngredientSnapshot:
    held: FoodId | None
    plate: PlateSnapshot
    pot: PotSnapshot = PotSnapshot()

    def __post_init__(self):
        if self.held is not None:
            _validate_food((self.held,))
        if not isinstance(self.plate, PlateSnapshot):
            raise ValueError("plate must be a PlateSnapshot.")
        if not isinstance(self.pot, PotSnapshot):
            raise ValueError("pot must be a PotSnapshot.")
        if self.held is not None and self.plate.location is not PlateLocation.DOCKED:
            raise ValueError("The chef can carry either food or the plate.")


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str


@dataclass(frozen=True)
class OrderSnapshot:
    order_id: int
    recipe_name: str
    required: tuple[FoodId, ...]
    remaining_seconds: float
    status: Literal["pending", "accepted"] = "pending"

    def __post_init__(self):
        _nonnegative_integer(self.order_id, "order_id")
        _validate_food(self.required)
        if not isfinite(self.remaining_seconds) or self.remaining_seconds < 0:
            raise ValueError("remaining_seconds must be finite and nonnegative.")
        if self.status not in ("pending", "accepted"):
            raise ValueError("Invalid order status.")


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
