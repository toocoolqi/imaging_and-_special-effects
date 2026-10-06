"""Select an object. Never collect food or complete orders here."""
from math import hypot, isfinite
from collections.abc import Iterable

from restaurant.shared.contracts import InteractionTarget


def choose_target(position: tuple[float, float],
                  targets: Iterable[InteractionTarget],
                  radius: float = 64.0) -> InteractionTarget | None:
    """Nearest point within radius; equal distances use target_id alphabetically.

    Facing is deliberately irrelevant, as specified in the team's shared plan.
    The scene owner places targets on reachable floor beside their objects.
    """
    if not isfinite(radius) or radius < 0 or not all(map(isfinite, position)):
        raise ValueError("Position and radius must be finite; radius cannot be negative.")
    candidates = []
    seen = set()
    for target in targets:
        if target.target_id in seen:
            raise ValueError(f"Duplicate target ID: {target.target_id}")
        seen.add(target.target_id)
        distance = hypot(target.x - position[0], target.y - position[1])
        if distance <= radius:
            candidates.append((distance, target.target_id, target))
    return min(candidates, key=lambda item: item[:2])[2] if candidates else None
