"""Four-direction animated chef. Only Arcade and Python's standard library."""
from math import ceil, hypot, isfinite
from pathlib import Path

import arcade

from restaurant.shared.contracts import Direction
from restaurant.shared.settings import (
    FRAME_SECONDS, KITCHEN_WIDTH, PLAYER_SCALE, PLAYER_SPEED, WINDOW_HEIGHT,
)

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "player"
VECTORS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
# Same rectangle for EVERY frame; animation never changes collision dimensions.
HIT_BOX = ((-24, -43), (24, -43), (24, 43), (-24, 43))


def movement_vector(keys) -> tuple[float, float]:
    """Opposites cancel; diagonals have the same speed as straight movement."""
    x = int("right" in keys) - int("left" in keys)
    y = int("up" in keys) - int("down" in keys)
    length = hypot(x, y)
    return (x / length, y / length) if length else (0.0, 0.0)


class PlayerController:
    def __init__(self, spawn: tuple[float, float]):
        self._walk = {direction: [self._load(f"{direction}_{i}.png") for i in range(4)]
                      for direction in VECTORS}
        # The source has only a front-facing idle column. Other directions freeze
        # a walking frame so the chef keeps facing the correct way while stopped.
        self._idle = {direction: frames[0] for direction, frames in self._walk.items()}
        self._idle["down"] = self._load("idle_0.png")
        self.sprite = arcade.Sprite(self._idle["down"], scale=PLAYER_SCALE)
        self._engine = None
        self._walls = None
        self._keys: list[Direction] = []  # Press order settles diagonal facing.
        self.reset(spawn)

    @staticmethod
    def _load(name: str) -> arcade.Texture:
        path = ASSET_DIR / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing chef frame: {path}. Copy assets/player with the code.")
        source = arcade.load_texture(path)
        return arcade.Texture(source.image, hit_box_points=HIT_BOX)

    @property
    def position(self) -> tuple[float, float]:
        return self.sprite.center_x, self.sprite.center_y

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def state(self) -> str:
        return "walk" if self.is_moving else "idle"

    def set_move_key(self, key: Direction, pressed: bool) -> None:
        if key not in VECTORS:
            raise ValueError(f"Unknown movement direction: {key}")
        if pressed and key not in self._keys:
            self._keys.append(key)
        elif not pressed and key in self._keys:
            self._keys.remove(key)

    def clear_input(self) -> None:
        """Call when pausing, changing scenes, or losing keyboard focus."""
        self._keys.clear()
        self.is_moving = False
        self._animation_time = 0.0
        self.sprite.change_x = self.sprite.change_y = 0.0
        self.sprite.texture = self._idle[self._direction]

    def reset(self, spawn: tuple[float, float]) -> None:
        if not all(map(isfinite, spawn)):
            raise ValueError("Spawn coordinates must be finite.")
        self.sprite.position = spawn
        self._direction: Direction = "down"
        self.clear_input()
        self._clamp_to_kitchen()

    def _clamp_to_kitchen(self) -> None:
        half_width, half_height = 24 * PLAYER_SCALE, 43 * PLAYER_SCALE
        self.sprite.center_x = max(half_width, min(KITCHEN_WIDTH - half_width, self.sprite.center_x))
        self.sprite.center_y = max(half_height, min(WINDOW_HEIGHT - half_height, self.sprite.center_y))

    def update(self, delta_time: float, walls: arcade.SpriteList) -> None:
        """Move/collide/animate exactly once per scene update.

        walls is the scene's shared SpriteList of solid, static rectangles.
        Do not also call sprite.update() or SpriteList.update() on this chef.
        """
        if not isfinite(delta_time) or delta_time < 0:
            raise ValueError("delta_time must be finite and nonnegative.")
        if delta_time == 0:
            return
        x, y = movement_vector(self._keys)
        previous_direction = self._direction
        for key in reversed(self._keys):
            vx, vy = VECTORS[key]
            if vx * x + vy * y > 0:
                self._direction = key
                break
        if walls is not self._walls:
            self._walls = walls
            self._engine = arcade.PhysicsEngineSimple(self.sprite, walls)

        # Bound a stalled frame to 0.25 seconds to avoid a teleport after a pause.
        # Each physics step travels <= 2 pixels, including at thin counter edges.
        dt = min(delta_time, 0.25)
        steps = max(1, ceil(PLAYER_SPEED * dt / 2))
        travelled = 0.0
        for _ in range(steps):
            before = self.position
            self.sprite.change_x = x * PLAYER_SPEED * dt / steps
            self.sprite.change_y = y * PLAYER_SPEED * dt / steps
            if x or y:
                self._engine.update()
                self._clamp_to_kitchen()
            travelled += hypot(self.position[0] - before[0], self.position[1] - before[1])
        self.sprite.change_x = self.sprite.change_y = 0.0
        self.is_moving = travelled > 0.001
        if not self.is_moving or previous_direction != self._direction:
            self._animation_time = 0.0
        if self.is_moving:
            self._animation_time += dt
            index = int(self._animation_time / FRAME_SECONDS) % 4
            self.sprite.texture = self._walk[self._direction][index]
        else:
            self.sprite.texture = self._idle[self._direction]
