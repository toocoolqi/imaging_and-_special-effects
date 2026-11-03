"""Visible furniture and measured floor footprints, in world pixels.

Pictures include raised surfaces. Solids cover their bases on the floor,
without an invisible buffer around the picture.
"""
from dataclasses import dataclass

from restaurant.shared.contracts import InteractionTarget

KITCHEN_WIDTH, KITCHEN_HEIGHT = 960, 704
SIDE_WALL_WIDTH, BOTTOM_WALL_HEIGHT, BACK_ROW_DEPTH = 18, 18, 104
FLOOR_TOP = KITCHEN_HEIGHT - BACK_ROW_DEPTH
SPAWN = (480.0, 220.0)


@dataclass(frozen=True)
class KitchenProp:
    prop_id: str
    asset: str
    x: int
    y: int
    width: int
    height: int
    # Local (x, y, width, height) of the base; None for tabletop decorations.
    footprint: tuple[int, int, int, int] | None = None
    support: str | None = None

    @property
    def solid(self):
        return self.footprint is not None

    @property
    def rectangle(self):
        return self.x, self.y, self.width, self.height

    @property
    def collision_rectangle(self):
        if self.footprint is None:
            raise ValueError(f"{self.prop_id} is supported by other furniture")
        dx, dy, width, height = self.footprint
        return self.x + dx, self.y + dy, width, height

    @property
    def depth_y(self):
        """Front of base: chef behind furniture is drawn before furniture."""
        _, y, _, height = self.collision_rectangle
        return y - height / 2


PROPS = (
    KitchenProp("crate_1", "crate_sandwich", 100, 104, 70, 90, (0, -20, 60, 46)),
    KitchenProp("crate_2", "crate_tomato", 190, 104, 70, 90, (0, -20, 60, 46)),
    KitchenProp("crate_3", "crate_noodles", 280, 104, 70, 90, (0, -20, 60, 46)),
    KitchenProp("crate_4", "crate_milk", 370, 104, 70, 90, (0, -20, 60, 46)),
    KitchenProp("plate_counter", "table", 620, 350, 180, 110, (0, -21, 164, 62)),
    KitchenProp("chopping_table", "table", 300, 350, 180, 110, (0, -21, 164, 62)),
    KitchenProp("serving_table", "pass_counter", 744, 526, 256, 90, (0, -22, 240, 40)),
    KitchenProp("wash_counter", "sink", 132, 526, 210, 98, (0, -28, 196, 40)),
    KitchenProp("floor_stove", "stove", 332, 526, 124, 119, (0, -21, 110, 70)),
    KitchenProp("floor_bin", "bin", 886, 112, 50, 70, (0, -17, 42, 32)),
    KitchenProp("chopping_board", "clean_board", 300, 382, 76, 35, support="chopping_table"),
    KitchenProp("display_plate", "plate", 620, 381, 66, 45, support="plate_counter"),
    # Pot bottom sits on the front-left burner; other burners remain visible.
    KitchenProp("display_pot", "pot", 307, 559, 46, 37, support="floor_stove"),
)
# Wall-mounted decoration does not occupy the walkable floor. Atlas artwork
# follows the same straight-on low top-down viewpoint as the original props.
WALL_ART = (
    ("spice_shelf", 132, 648, 190, 94),
    ("extractor", 378, 646, 220, 111),
    ("service_hatch", 744, 630, 256, 112),
)
ROOM_SOLIDS = (
    (KITCHEN_WIDTH / 2, BOTTOM_WALL_HEIGHT / 2, KITCHEN_WIDTH, BOTTOM_WALL_HEIGHT),
    (SIDE_WALL_WIDTH / 2, KITCHEN_HEIGHT / 2, SIDE_WALL_WIDTH, KITCHEN_HEIGHT),
    (KITCHEN_WIDTH - SIDE_WALL_WIDTH / 2, KITCHEN_HEIGHT / 2,
     SIDE_WALL_WIDTH, KITCHEN_HEIGHT),
    (KITCHEN_WIDTH / 2, KITCHEN_HEIGHT - BACK_ROW_DEPTH / 2,
     KITCHEN_WIDTH, BACK_ROW_DEPTH),
)
SOLID_PROPS = tuple(prop for prop in PROPS if prop.solid)
WALL_RECTANGLES = ROOM_SOLIDS + tuple(prop.collision_rectangle for prop in SOLID_PROPS)

# Targets describe the chef CENTER when standing at a station. A selected
# foot ring is drawn 32 pixels below that center. IDs stay stable for teammates.
TARGETS = (
    InteractionTarget("box_sandwich", "box", 100, 174, "sandwich"),
    InteractionTarget("box_tomato", "box", 190, 174, "tomato"),
    InteractionTarget("box_noodles", "box", 280, 174, "noodles"),
    InteractionTarget("box_milk", "box", 370, 174, "milk"),
    InteractionTarget("plate", "plate", 620, 302),
    InteractionTarget("chopping_board", "chop", 300, 302),
    InteractionTarget("bin", "bin", 886, 174),
    InteractionTarget("serve", "serve", 744, 472),
)
TARGET_LABELS = {
    "box_sandwich": "Pantry", "box_tomato": "Pantry",
    "box_noodles": "Pantry", "box_milk": "Pantry",
    "plate": "Plate station", "chopping_board": "Chopping board",
    "bin": "Bin", "serve": "Service hatch",
}
ANIMATION_TEST_POSITION = (480, 420)
