"""One low top-down room: the same floor and furniture style from edge to edge.

Every floor-standing prop has a full-size collision rectangle. Small objects
resting on a table inherit that table's collision. The chef is approximately
one counter high; the aisles are laid out for the enlarged, fixed hitbox.
"""
from dataclasses import dataclass

from restaurant.shared.contracts import InteractionTarget

KITCHEN_WIDTH, KITCHEN_HEIGHT = 1024, 768
SIDE_WALL_WIDTH, BOTTOM_WALL_HEIGHT, BACK_ROW_DEPTH = 24, 24, 24
FLOOR_TOP = KITCHEN_HEIGHT - BACK_ROW_DEPTH
SPAWN = (500.0, 180.0)


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
    KitchenProp("crate_1", "crate_sandwich", 120, 650, 70, 90),
    KitchenProp("crate_2", "crate_tomato", 260, 650, 70, 90),
    KitchenProp("crate_3", "crate_noodles", 400, 650, 70, 90),
    KitchenProp("crate_4", "crate_milk", 540, 650, 70, 90),
    KitchenProp("plate_counter", "table", 280, 340, 190, 116),
    KitchenProp("chopping_table", "table", 740, 420, 190, 116),
    KitchenProp("serving_table", "table", 740, 150, 190, 116),
    KitchenProp("floor_stove", "stove", 880, 650, 120, 115),
    KitchenProp("floor_bin", "bin", 940, 140, 54, 76),
    KitchenProp("chopping_board", "board", 740, 452, 90, 43, False, "chopping_table"),
    KitchenProp("display_plate", "plate", 280, 370, 80, 54, False, "plate_counter"),
    KitchenProp("display_pot", "pot", 880, 675, 62, 50, False, "floor_stove"),
    KitchenProp("display_sandwich", "sandwich", 710, 181, 35, 38, False, "serving_table"),
    KitchenProp("display_tomato", "tomato", 755, 182, 30, 31, False, "serving_table"),
    KitchenProp("display_noodles", "noodles", 307, 370, 29, 28, False, "plate_counter"),
    KitchenProp("display_milk", "milk", 221, 373, 24, 37, False, "plate_counter"),
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
    InteractionTarget("box_lettuce", "box", 120, 535, "lettuce"),
    InteractionTarget("box_tomato", "box", 260, 535, "tomato"),
    InteractionTarget("box_bread", "box", 400, 535, "bread"),
    InteractionTarget("box_cheese", "box", 540, 535, "cheese"),
    InteractionTarget("plate", "plate", 280, 210),
    InteractionTarget("chopping_board", "chop", 740, 290),
    InteractionTarget("bin", "bin", 940, 250),
    InteractionTarget("serve", "serve", 590, 150),
)
TARGET_LABELS = {
    "box_lettuce": "Crate display", "box_tomato": "Crate display",
    "box_bread": "Crate display", "box_cheese": "Crate display",
    "plate": "Plate station", "chopping_board": "Chopping board",
    "bin": "Bin", "serve": "Serving table",
}
ANIMATION_TEST_POSITION = (520, 440)  # A clear patch for animation checks.
