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
        islands = {"plate_counter", "display_plate", "chopping_table", "chopping_board"}
        props = tuple(replace(prop, x=920 - prop.x) if prop.prop_id in islands else prop
                      for prop in PROPS)
        targets = tuple(replace(target, x=920 - target.x) if target.kind in ("plate", "chop")
                        else target for target in TARGETS)
    else:
        props, targets = PROPS, TARGETS
    return KitchenDay(name, style, props, targets)


DAYS = (
    kitchen_day("Warm Kitchen", "warm"),
    kitchen_day("Silver Kitchen", "metal"),
    kitchen_day("Overgrown Kitchen", "overgrown"),
    kitchen_day("Damaged Silver Kitchen", "metal_damaged"),
)
