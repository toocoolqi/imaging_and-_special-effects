"""Four service days using the same station rules and different room treatments."""
from dataclasses import dataclass, replace

from restaurant.kitchen.layout import PROPS, ROOM_SOLIDS, SPAWN, TARGETS


@dataclass(frozen=True)
class KitchenDay:
    name: str
    style: str
    props: tuple
    targets: tuple
    spawn: tuple = SPAWN

    @property
    def walls(self):
        return ROOM_SOLIDS + tuple(prop.collision_rectangle for prop in self.props if prop.solid)


def kitchen_day(name, style):
    if style.startswith("metal"):
        offsets = {"plate_counter": -320, "display_plate": -320,
                   "chopping_table": 320, "chopping_board": 320}
        props = tuple(replace(prop, x=prop.x + offsets.get(prop.prop_id, 0)) for prop in PROPS)
        target_offsets = {"plate": -320, "chop": 320}
        targets = tuple(replace(target, x=target.x + target_offsets.get(target.kind, 0))
                        for target in TARGETS)
    else:
        props, targets = PROPS, TARGETS
    return KitchenDay(name, style, props, targets)


DAYS = (
    kitchen_day("Warm Kitchen", "warm"),
    kitchen_day("Silver Kitchen", "metal"),
    kitchen_day("Overgrown Kitchen", "overgrown"),
    kitchen_day("Damaged Silver Kitchen", "metal_damaged"),
)
