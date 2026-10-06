"""All dimensions use world pixels; (0, 0) is the bottom-left corner."""
from restaurant.shared.contracts import InteractionTarget

WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 720
KITCHEN_WIDTH = 900
SIDEBAR_BOUNDS = (900, 0, 300, 720)
SPAWN = (450.0, 170.0)
PLAYER_SPEED = 200.0
PLAYER_SCALE = 0.65
FRAME_SECONDS = 0.14
INTERACTION_RADIUS = 64.0
# (center_x, center_y, width, height). Solid, axis-aligned, stationary rectangles.
WALL_RECTANGLES = (
    (450, 10, 900, 20), (450, 710, 900, 20),
    (10, 360, 20, 720), (890, 360, 20, 720),
    (130, 600, 130, 70), (320, 600, 130, 70),
    (510, 600, 130, 70), (700, 600, 130, 70),
    (450, 360, 240, 80),
    (130, 120, 130, 70), (750, 120, 170, 70),
)
TARGETS = (
    InteractionTarget("box_lettuce", "box", 130, 520, "lettuce"),
    InteractionTarget("box_tomato", "box", 320, 520, "tomato"),
    InteractionTarget("box_bread", "box", 510, 520, "bread"),
    InteractionTarget("box_cheese", "box", 700, 520, "cheese"),
    InteractionTarget("plate", "plate", 450, 275),
    InteractionTarget("bin", "bin", 130, 205),
    InteractionTarget("serve", "serve", 750, 205),
)
