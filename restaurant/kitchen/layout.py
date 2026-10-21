"""Single map for furniture, collision rectangles and floor approach points.

The upper strip contains the original wall/cupboards/appliances and is solid.
Every floor-standing prop has a full-size rectangle, including its legs/front.
Objects resting on a table inherit the table's collision.
"""
from dataclasses import dataclass

from restaurant.shared.contracts import InteractionTarget

KITCHEN_WIDTH, KITCHEN_HEIGHT = 1280, 960
SIDE_WALL_WIDTH, BOTTOM_WALL_HEIGHT, BACK_ROW_DEPTH = 40, 28, 235
FLOOR_TOP = KITCHEN_HEIGHT - BACK_ROW_DEPTH
SPAWN = (585.0, 120.0)


@dataclass(frozen=True)
class KitchenProp:
    prop_id: str
    asset: str
    x: int
    y: int
    width: int
    height: int
    solid: bool = True
    support: str | None = None

    @property
    def rectangle(self):
        return self.x, self.y, self.width, self.height


# Edit furniture position and visible size together here.
PROPS = (
    KitchenProp("crate_1", "crate_sandwich", 145, 562, 94, 122),
    KitchenProp("crate_2", "crate_tomato", 275, 562, 94, 122),
    KitchenProp("crate_3", "crate_noodles", 405, 562, 94, 122),
    KitchenProp("crate_4", "crate_milk", 535, 562, 94, 122),
    KitchenProp("plate_counter", "table", 325, 225, 280, 170),
    KitchenProp("chopping_table", "table", 795, 450, 250, 152),
    KitchenProp("serving_table", "table", 790, 155, 250, 152),
    KitchenProp("floor_stove", "stove", 1065, 555, 142, 136),
    KitchenProp("floor_bin", "bin", 1070, 140, 66, 92),
    KitchenProp("chopping_board", "board", 795, 494, 116, 56, False, "chopping_table"),
    KitchenProp("display_plate", "plate", 325, 271, 108, 73, False, "plate_counter"),
    KitchenProp("display_pot", "pot", 1065, 590, 77, 62, False, "floor_stove"),
    KitchenProp("display_sandwich", "sandwich", 750, 199, 43, 47, False, "serving_table"),
    KitchenProp("display_tomato", "tomato", 805, 201, 37, 38, False, "serving_table"),
    KitchenProp("display_noodles", "noodles", 362, 272, 38, 36, False, "plate_counter"),
    KitchenProp("display_milk", "milk", 249, 275, 30, 47, False, "plate_counter"),
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
WALL_RECTANGLES = ROOM_SOLIDS + tuple(prop.rectangle for prop in SOLID_PROPS)

# Approach points are on FLOOR. Keep the teammates' existing ingredient IDs;
# pictured foods are decorative artwork and do not define working recipes.
TARGETS = (
    InteractionTarget("box_lettuce", "box", 145, 442, "lettuce"),
    InteractionTarget("box_tomato", "box", 275, 442, "tomato"),
    InteractionTarget("box_bread", "box", 405, 442, "bread"),
    InteractionTarget("box_cheese", "box", 535, 442, "cheese"),
    InteractionTarget("plate", "plate", 325, 84),
    InteractionTarget("chopping_board", "chop", 795, 318),
    InteractionTarget("bin", "bin", 1070, 242),
    InteractionTarget("serve", "serve", 640, 155),
)
TARGET_LABELS = {
    "box_lettuce": "Crate display", "box_tomato": "Crate display",
    "box_bread": "Crate display", "box_cheese": "Crate display",
    "plate": "Plate station", "chopping_board": "Chopping board",
    "bin": "Bin", "serve": "Serving table",
}
ANIMATION_TEST_POSITION = (620, 355)  # A clear patch for animation checks.
