"""Order data: the menu, the tuning for one day, and the private order record.

Pure Python: importing this module never imports Arcade or opens a window.
"""
from dataclasses import dataclass
from math import isfinite
from typing import get_args

from restaurant.shared.contracts import DishId, FoodId, IngredientId, PreparedFoodId

_FOOD_IDS = get_args(IngredientId) + get_args(PreparedFoodId) + get_args(DishId)
MAX_RECIPE_ITEMS = 4  # the shared plate holds four portions


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    name: str
    required: tuple[FoodId, ...]
    base_gold: int
    by_hand: bool = False   # one item the chef may hand over without the plate

    def __post_init__(self):
        if not self.recipe_id or not self.name:
            raise ValueError("A recipe needs an ID and a display name.")
        if not isinstance(self.required, tuple) or not self.required:
            raise ValueError("required must be a non-empty tuple of food IDs.")
        if len(self.required) > MAX_RECIPE_ITEMS:
            raise ValueError(f"A recipe cannot need more than {MAX_RECIPE_ITEMS} items.")
        if any(item not in _FOOD_IDS for item in self.required):
            raise ValueError(f"Unknown food in recipe {self.recipe_id!r}.")
        if self.by_hand and len(self.required) != 1:
            raise ValueError("Only single-item recipes can be served by hand.")
        if type(self.base_gold) is not int or self.base_gold <= 0:
            raise ValueError("base_gold must be a positive integer.")


# The whole menu in one place. A raw tomato and a chopped tomato both count
# as "tomato" (see restaurant.ingredients.system.recipe_item).
RECIPES: tuple[Recipe, ...] = (
    Recipe("sandwich", "Sandwich", ("sandwich",), 30, by_hand=True),
    Recipe("milk", "Milk", ("milk",), 30, by_hand=True),
    Recipe("tomato_sandwich", "Tomato sandwich", ("sandwich", "tomato"), 60),
    Recipe("lunch_set", "Lunch set", ("sandwich", "milk"), 50),
    Recipe("pasta", "Pasta", ("pasta",), 90),
)
RECIPE_BY_ID = {recipe.recipe_id: recipe for recipe in RECIPES}
if len(RECIPE_BY_ID) != len(RECIPES):
    raise ValueError("Recipe IDs must be unique.")
HAND_SERVICE_ITEMS = tuple(recipe.required[0] for recipe in RECIPES if recipe.by_hand)


@dataclass(frozen=True)
class DayRules:
    """Tuning for one restaurant day. All times are in seconds."""
    target_gold: int = 200              # gold that completes the day
    patience_seconds: float = 90.0      # how long an order waits, from its arrival
    arrival_seconds: float = 10.0       # average gap between new customers
    max_cards: int = 3                  # never more orders on screen than this
    tip_max: int = 30                   # extra gold for an instant delivery
    recipe_ids: tuple[str, ...] = tuple(recipe.recipe_id for recipe in RECIPES)

    def __post_init__(self):
        if type(self.target_gold) is not int or self.target_gold <= 0:
            raise ValueError("target_gold must be a positive integer.")
        for name in ("patience_seconds", "arrival_seconds"):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite.")
        if type(self.max_cards) is not int or self.max_cards < 1:
            raise ValueError("max_cards must be at least 1.")
        if type(self.tip_max) is not int or self.tip_max < 0:
            raise ValueError("tip_max must be a nonnegative integer.")
        if not self.recipe_ids or any(r not in RECIPE_BY_ID for r in self.recipe_ids):
            raise ValueError("recipe_ids must name recipes from the menu.")


@dataclass
class _Order:
    """Owned exclusively by OrderSystem; callers only ever see snapshots."""
    order_id: int
    recipe: Recipe
    status: str          # always "accepted": orders are live from the moment they arrive
    remaining: float     # seconds left before the customer gives up
