"""Four-direction animated chef. Only Arcade and Python's standard library."""
from math import ceil, hypot, isfinite
from pathlib import Path

import arcade

from restaurant.pixel_art import draw_pixel_texture
from restaurant.shared.contracts import Direction
from restaurant.shared.settings import (
    FRAME_SECONDS, KITCHEN_HEIGHT, KITCHEN_WIDTH, PLAYER_SCALE, PLAYER_SPEED,
)

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "player" / "animated"
VISUAL_SCALE = 2
VISUAL_HEIGHT = 184
FRAME_CENTER_ABOVE_FEET = 78
PICKUP_SECONDS = 0.16
UNCHANGED = object()
VECTORS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
# A top-down character collides at the feet, not with the hat and shoulders.
# Keep this footprint across every frame and visual size.
FOOT_HALF_WIDTH, FOOT_HALF_HEIGHT, FOOT_OFFSET_Y = 16, 10, -32
HIT_BOX = ((-16, -42), (16, -42), (16, -22), (-16, -22))
# Pixel bounds of the leading hand for standing, step one, step two and
# passing poses. The coordinate origin is the upper-left of each source frame.
HAND_AREAS = {
    "down": ((73, 69, 8, 8), (74, 67, 6, 6), (70, 68, 10, 10), (73, 63, 8, 10)),
    "up": ((73, 70, 8, 8), (73, 67, 6, 6), (74, 68, 6, 10), (72, 63, 6, 6)),
    "left": ((48, 73, 4, 6), (45, 67, 6, 8), (43, 67, 10, 8), (44, 65, 8, 8)),
    "right": ((69, 71, 4, 8), (69, 66, 8, 8), (64, 67, 10, 8), (62, 69, 10, 8)),
}


def movement_vector(keys) -> tuple[float, float]:
    """Opposites cancel; diagonals have the same speed as straight movement."""
    x = int("right" in keys) - int("left" in keys)
    y = int("up" in keys) - int("down" in keys)
    length = hypot(x, y)
    return (x / length, y / length) if length else (0.0, 0.0)


class PlayerController:
    def __init__(self, spawn: tuple[float, float]):
        self._frames = {direction: [self._load(f"{direction}_{i}.png") for i in range(8)]
                        for direction in VECTORS}
        self._chop_frames = [self._load(f"chop_{i}.png") for i in range(4)]
        self.sprite = arcade.Sprite(self._frames["down"][0], scale=PLAYER_SCALE)
        self._hand_crops = {}
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
    def ground_position(self) -> tuple[float, float]:
        """Center of the feet, for depth sorting and ground effects.

        position remains the sprite center used by existing station hooks.
        """
        return self.sprite.center_x, self.sprite.center_y + FOOT_OFFSET_Y * PLAYER_SCALE

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def pose(self) -> str:
        if self.chopping:
            return "chop"
        return "walk" if self.is_moving else "idle"

    @property
    def state(self) -> str:
        return self.pose

    @property
    def visual_height(self) -> int:
        return VISUAL_HEIGHT

    @property
    def plate_anchor(self):
        """Where plated food sits in the current pose. The rear view hides it."""
        if not self.carrying_plate or self.chopping or self.direction == "up":
            return None
        x, y = self.ground_position
        return (x + {"down": 0, "left": -32, "right": 30}[self.direction],
                y + {"down": 34, "left": 39, "right": 43}[self.direction])

    @property
    def hand_anchor(self):
        """Follow the palm in each pose, settling as the chef lifts new food."""
        if self.carrying_plate or self.chopping:
            return None
        left, top, width, height = HAND_AREAS[self.direction][self._frame_index]
        x, y = self._art_position(left + width / 2, top + height / 2)
        sign = -1 if self.direction == "left" else 1
        lift = self._pickup_progress
        return x + sign * (9 + 5 * (1 - lift)), y + 7 - 11 * (1 - lift)

    @property
    def _pickup_progress(self):
        fraction = self._pickup_elapsed / PICKUP_SECONDS
        return 1 - (1 - fraction) ** 2

    @property
    def hand_item_size(self):
        return 27 * (.72 + .28 * self._pickup_progress)

    def _art_position(self, source_x, source_y):
        x, y = self.ground_position
        texture = self.sprite.texture
        return (x + (source_x - texture.width / 2) * VISUAL_SCALE,
                y + FRAME_CENTER_ABOVE_FEET + (texture.height / 2 - source_y) * VISUAL_SCALE)

    def draw_grip(self):
        """Put the fingers over the edge of food drawn in front of the chef."""
        key = self.direction, self._frame_index
        left, top, width, height = HAND_AREAS[self.direction][self._frame_index]
        if key not in self._hand_crops:
            self._hand_crops[key] = self.sprite.texture.crop(left, top, width, height)
        x, y = self._art_position(left + width / 2, top + height / 2)
        draw_pixel_texture(self._hand_crops[key], arcade.XYWH(
            x, y, width * VISUAL_SCALE, height * VISUAL_SCALE))

    def draw(self):
        x, y = self.ground_position
        texture = self.sprite.texture
        draw_pixel_texture(texture, arcade.XYWH(
            x, y + FRAME_CENTER_ABOVE_FEET, texture.width * VISUAL_SCALE,
            texture.height * VISUAL_SCALE))

    def set_visual_state(self, *, carrying_plate=None, chopping=None, held=UNCHANGED):
        if held is not UNCHANGED and held != self._held:
            self._held = held
            self._pickup_elapsed = 0.0 if held is not None else PICKUP_SECONDS
        changed = False
        if carrying_plate is not None and self.carrying_plate != carrying_plate:
            self.carrying_plate = carrying_plate
            changed = True
        if chopping is not None and self.chopping != chopping:
            self.chopping = chopping
            changed = True
            if chopping:
                self._direction = "up"
                self.is_moving = False
        if changed:
            self._animation_time = 0.0
            self._set_frame()

    def _set_frame(self):
        if self.chopping:
            index = int(self._animation_time / .11) % len(self._chop_frames)
            texture = self._chop_frames[index]
        else:
            base = 4 if self.carrying_plate else 0
            index = 0
            if self.is_moving:
                # Contact, passing, opposite contact, passing.
                index = (1, 3, 2, 3)[int(self._animation_time / FRAME_SECONDS) % 4]
            self._frame_index = index
            texture = self._frames[self._direction][base + index]
        if texture is not self.sprite.texture:
            self.sprite.texture = texture

    def set_move_key(self, key: Direction, pressed: bool) -> None:
        if key not in VECTORS:
            raise ValueError(f"Unknown movement direction: {key}")
        if pressed and key not in self._keys:
            self._keys.append(key)
        elif not pressed and key in self._keys:
            self._keys.remove(key)
            if movement_vector(self._keys) == (0.0, 0.0):
                self.is_moving = False
                self._animation_time = 0.0
                self._set_frame()

    def clear_input(self) -> None:
        """Call when pausing, changing scenes, or losing keyboard focus."""
        self._keys.clear()
        self.is_moving = False
        self._animation_time = 0.0
        self.sprite.change_x = self.sprite.change_y = 0.0
        self._set_frame()

    def reset(self, spawn: tuple[float, float]) -> None:
        if not all(map(isfinite, spawn)):
            raise ValueError("Spawn coordinates must be finite.")
        self.carrying_plate = self.chopping = False
        self._held = None
        self._pickup_elapsed = PICKUP_SECONDS
        self.sprite.position = spawn
        self._direction: Direction = "down"
        self.clear_input()
        self._clamp_to_kitchen()

    def _clamp_to_kitchen(self) -> None:
        half_width, half_height = FOOT_HALF_WIDTH * PLAYER_SCALE, FOOT_HALF_HEIGHT * PLAYER_SCALE
        offset = FOOT_OFFSET_Y * PLAYER_SCALE
        self.sprite.center_x = max(half_width, min(KITCHEN_WIDTH - half_width, self.sprite.center_x))
        self.sprite.center_y = max(half_height - offset,
                                   min(KITCHEN_HEIGHT - half_height - offset, self.sprite.center_y))

    def update(self, delta_time: float, walls: arcade.SpriteList) -> None:
        """Move/collide/animate exactly once per scene update.

        walls is the scene's shared SpriteList of solid, static rectangles.
        Do not also call sprite.update() or SpriteList.update() on this chef.
        """
        if not isfinite(delta_time) or delta_time < 0:
            raise ValueError("delta_time must be finite and nonnegative.")
        if delta_time == 0:
            return
        self._pickup_elapsed = min(PICKUP_SECONDS, self._pickup_elapsed + delta_time)
        if self.chopping:
            self._animation_time += delta_time
            self._set_frame()
            return
        x, y = movement_vector(self._keys)
        previous_direction = self._direction
        for key in reversed(self._keys):
            vx, vy = VECTORS[key]
            if vx * x + vy * y > 0:
                self._direction = key
                break
        # Bound a stalled frame to 0.25 seconds to avoid a teleport after a pause.
        # Each physics step travels <= 2 pixels, including at thin counter edges.
        dt = min(delta_time, 0.25)
        steps = max(1, ceil(PLAYER_SPEED * dt / 2))
        start = self.position
        for _ in range(steps):
            if x or y:
                self._move_axis(0, x * PLAYER_SPEED * dt / steps, walls)
                self._move_axis(1, y * PLAYER_SPEED * dt / steps, walls)
                self._clamp_to_kitchen()
        self.sprite.change_x = self.sprite.change_y = 0.0
        self.is_moving = hypot(self.position[0] - start[0], self.position[1] - start[1]) > 0.01
        if not self.is_moving or previous_direction != self._direction:
            self._animation_time = 0.0
        if self.is_moving:
            self._animation_time += dt
        self._set_frame()

    def _move_axis(self, axis, amount, walls):
        """Use Arcade's hit boxes with subpixel stopping and wall sliding.

        PhysicsEngineSimple resolves vertical overlaps in whole/quarter pixels.
        At a fractional movement speed that can bounce the feet every frame.
        These tiny bounded steps instead stop at the last noncolliding position.
        """
        if not amount:
            return
        start = list(self.position)
        end = start.copy()
        end[axis] += amount
        self.sprite.position = tuple(end)
        if not arcade.check_for_collision_with_list(self.sprite, walls):
            return
        low, high = 0.0, 1.0
        for _ in range(10):
            mid = (low + high) / 2
            end[axis] = start[axis] + amount * mid
            self.sprite.position = tuple(end)
            if arcade.check_for_collision_with_list(self.sprite, walls):
                high = mid
            else:
                low = mid
        end[axis] = start[axis] + amount * low
        self.sprite.position = tuple(end)
