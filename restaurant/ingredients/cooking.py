"""One stove pot for the creamy noodles recipe."""
from restaurant.shared.contracts import ActionResult

COOK_SECONDS = 4.0
REQUIRED = {"noodles", "milk"}


class CookingPot:
    def __init__(self):
        self.reset()

    def reset(self):
        self.loaded = set()
        self.elapsed = 0.0

    @property
    def state(self):
        if self.elapsed >= COOK_SECONDS:
            return "ready"
        if self.loaded == REQUIRED:
            return "cooking"
        return "loading" if self.loaded else "empty"

    def update(self, delta_time):
        if self.state == "cooking":
            self.elapsed = min(COOK_SECONDS, self.elapsed + delta_time)
            return self.state == "ready"
        return False

    def use(self, ingredients):
        hand = ingredients.snapshot()
        if self.state == "ready":
            result = ingredients.take_cooked_portion()
            if result.success:
                self.reset()
            return result
        if self.state == "cooking":
            return ActionResult(False, "The noodles are still cooking.")
        if hand.held not in REQUIRED:
            return ActionResult(False, "Bring one noodles and one milk to the pot.")
        if hand.held in self.loaded:
            return ActionResult(False, "That ingredient is already in the pot.")
        self.loaded.add(ingredients.take_held())
        message = "Cooking creamy noodles." if self.state == "cooking" else "Added to pot."
        return ActionResult(True, message)
