"""The chopping board holds one tomato until its prepared portion is taken."""
from math import isfinite

from restaurant.ingredients.system import IngredientSystem
from restaurant.shared.contracts import ActionResult

CHOP_SECONDS = 1.2


class ChoppingBoard:
    def __init__(self) -> None:
        self.reset()

    @property
    def state(self) -> str:
        if self._elapsed is None:
            return "idle"
        return "ready" if self._elapsed >= CHOP_SECONDS else "chopping"

    @property
    def progress(self) -> float:
        return 0.0 if self._elapsed is None else self._elapsed / CHOP_SECONDS

    def reset(self) -> None:
        self._elapsed: float | None = None

    def update(self, delta_time: float) -> bool:
        """Advance the current chop and report the completion edge once."""
        if not isfinite(delta_time) or delta_time < 0:
            raise ValueError("Chopping time must be finite and nonnegative.")
        if self.state != "chopping":
            return False
        self._elapsed = min(CHOP_SECONDS, self._elapsed + delta_time)
        return self.state == "ready"

    def use(self, ingredients: IngredientSystem) -> ActionResult:
        if self.state == "chopping":
            return ActionResult(False, "The tomato is still being chopped.")
        if self.state == "ready":
            result = ingredients.take_chopped_tomato()
            if result.success:
                self.reset()
            return result
        if not ingredients.take_tomato_for_chopping():
            return ActionResult(False, "Cutting board: bring a tomato by hand or on the plate.")
        self._elapsed = 0.0
        return ActionResult(True, "Chopping tomato.")
