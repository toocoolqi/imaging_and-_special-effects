"""Four service days: one kitchen layout each, its artwork, story and tuning.

The order follows the storyboard. The hero takes over an abandoned
restaurant; the gold earned each day pays for the renovation that the NEXT
day's kitchen shows:

    Day 1  Overgrown Kitchen       (art: warm_overgrown)  the abandoned diner
    Day 2  Warm Kitchen            (art: warm_clean)      the same room, restored
    Day 3  Damaged Silver Kitchen  (art: metal_damaged)   a second, run-down kitchen
    Day 4  Silver Kitchen          (art: metal_clean)     the same room, renovated

Clean and damaged twins share the same furniture, footprints and stations.
The silver rooms swap the plate and chopping islands, so they play differently.
Each day gets busier: shorter order timers, faster arrivals and a higher gold
target (so more orders), never more than three orders on screen. Change the
numbers in `rules` here only.
"""
from dataclasses import dataclass, field, replace
from pathlib import Path

from restaurant.kitchen.layout import PROPS, ROOM_SOLIDS, SPAWN, TARGETS
from restaurant.orders.models import DayRules

ART_ROOT = Path(__file__).resolve().parents[2] / "assets" / "kitchen"
# Map IDs from the environment guide; each names a folder under assets/kitchen.
MAP_IDS = {"warm": "warm_clean", "overgrown": "warm_overgrown",
           "metal": "metal_clean", "metal_damaged": "metal_damaged"}


@dataclass(frozen=True)
class KitchenDay:
    name: str
    style: str
    props: tuple
    targets: tuple
    spawn: tuple = SPAWN
    headline: str = ""
    story: str = ""
    music: str = "bgm_warm"
    rules: DayRules = field(default_factory=DayRules)
    # Floor/wall points used by BOTH the artwork (puddles, broken panels) and
    # the runtime ambience (water drips, sparks). Never solid.
    effect_points: tuple = ()
    shift_seconds: float = 180.0

    @property
    def map_id(self) -> str:
        return MAP_IDS[self.style]

    @property
    def art_dir(self) -> Path:
        return ART_ROOT / self.map_id

    @property
    def condition(self) -> str:
        return {"overgrown": "overgrown", "metal_damaged": "damaged"}.get(self.style, "clean")

    @property
    def walls(self):
        return ROOM_SOLIDS + tuple(prop.collision_rectangle for prop in self.props if prop.solid)


def kitchen_day(name, style, **details):
    if style.startswith("metal"):
        offsets = {"plate_counter": -320, "display_plate": -320,
                   "chopping_table": 320, "chopping_board": 320}
        props = tuple(replace(prop, x=prop.x + offsets.get(prop.prop_id, 0)) for prop in PROPS)
        target_offsets = {"plate": -320, "chop": 320}
        targets = tuple(replace(target, x=target.x + target_offsets.get(target.kind, 0))
                        for target in TARGETS)
    else:
        props, targets = PROPS, TARGETS
    return KitchenDay(name, style, props, targets, **details)


EASY = ("sandwich", "milk", "tomato_sandwich")
WITH_PASTA = EASY + ("pasta",)
FULL_MENU = WITH_PASTA + ("lunch_set",)

DAYS = (
    kitchen_day(
        "Overgrown Kitchen", "overgrown",
        headline="A forgotten kitchen",
        story="You left the office for good and took over an abandoned restaurant. "
              "Earn 150 gold to restore it.",
        rules=DayRules(150, patience_seconds=82.0, arrival_seconds=14.0, recipe_ids=EASY),
        effect_points=((150, 260), (500, 540), (845, 330))),
    kitchen_day(
        "Warm Kitchen", "warm",
        headline="Grand reopening",
        story="Yesterday's gold paid for the repairs. Word is out and customers are "
              "arriving faster: earn 220 gold.",
        shift_seconds=165.0,
        rules=DayRules(220, patience_seconds=68.0, arrival_seconds=11.0, recipe_ids=WITH_PASTA)),
    kitchen_day(
        "Damaged Silver Kitchen", "metal_damaged",
        headline="A second kitchen",
        story="You bought a run-down steel kitchen across town. Customers are impatient: "
              "earn 290 gold to renovate it.",
        music="bgm_metal",
        shift_seconds=150.0,
        rules=DayRules(290, patience_seconds=56.0, arrival_seconds=9.0, recipe_ids=FULL_MENU),
        effect_points=((247, 640), (599, 640))),
    kitchen_day(
        "Silver Kitchen", "metal",
        headline="The flagship",
        story="Rust gone, steel polished, and the rush never stops. Serve fast to finish "
              "your journey: earn 360 gold.",
        music="bgm_metal",
        shift_seconds=135.0,
        rules=DayRules(360, patience_seconds=45.0, arrival_seconds=7.5, recipe_ids=FULL_MENU)),
)
