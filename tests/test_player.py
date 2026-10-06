"""State, movement, real Arcade collision, and interaction regression checks."""
import math

import arcade
import pytest

from restaurant.player.controller import PlayerController, movement_vector
from restaurant.player.interaction import choose_target
from restaurant.shared.contracts import InteractionTarget
from restaurant.shared.settings import PLAYER_SCALE, TARGETS, WALL_RECTANGLES


def target(name, x, y=0):
    return InteractionTarget(name, "plate", x, y)


def walls_from_layout():
    walls = arcade.SpriteList(use_spatial_hash=True)
    for x, y, width, height in WALL_RECTANGLES:
        walls.append(arcade.SpriteSolidColor(width, height, x, y))
    return walls


@pytest.mark.parametrize("keys,expected", [
    ([], (0, 0)), (["left", "right"], (0, 0)),
    (["up", "down"], (0, 0)), (["up"], (0, 1)),
    (["up", "right"], (2 ** -0.5, 2 ** -0.5)),
])
def test_input_vector(keys, expected):
    assert movement_vector(keys) == pytest.approx(expected)


def test_target_boundary_ties_and_nearest():
    assert choose_target((0, 0), []) is None
    assert choose_target((0, 0), [target("outside", 64.01)]) is None
    assert choose_target((0, 0), [target("edge", 64)]).target_id == "edge"
    assert choose_target((0, 0), [target("diagonal", 48, 48)]) is None
    assert choose_target((0, 0), [target("b", -10), target("a", 10)]).target_id == "a"
    assert choose_target((0, 0), [target("far", 50), target("near", 5)]).target_id == "near"
    with pytest.raises(ValueError, match="Duplicate"):
        choose_target((0, 0), [target("same", 1), target("same", 2)])


@pytest.mark.parametrize("direction,axis,sign", [
    ("up", 1, 1), ("down", 1, -1), ("left", 0, -1), ("right", 0, 1),
])
def test_movement_animation_idle(direction, axis, sign):
    chef = PlayerController((450, 360))
    walls = arcade.SpriteList()
    chef.set_move_key(direction, True)
    chef.update(0.1, walls)
    first_walk = chef.sprite.texture
    chef.update(0.1, walls)
    assert chef.position[axis] == pytest.approx((450, 360)[axis] + sign * 40, abs=0.1)
    assert chef.sprite.texture is not first_walk
    assert chef.direction == direction
    assert chef.state == "walk"
    old_hitbox = chef.sprite.hit_box.points
    chef.set_move_key(direction, False)
    before = chef.position
    chef.update(0.1, walls)
    assert chef.position == before
    assert chef.direction == direction
    assert chef.state == "idle"
    assert chef.sprite.hit_box.points == old_hitbox


def test_timing_diagonal_and_facing():
    distances = []
    for rate in (30, 60, 144):
        chef = PlayerController((100, 100))
        chef.set_move_key("right", True)
        chef.set_move_key("up", True)
        for _ in range(rate):
            chef.update(1 / rate, arcade.SpriteList())
        distances.append(math.dist((100, 100), chef.position))
        assert chef.direction == "up"
    assert distances == pytest.approx([200, 200, 200], abs=1)
    chef.set_move_key("up", False)
    chef.update(0.1, arcade.SpriteList())
    assert chef.direction == "right"


@pytest.mark.parametrize("direction,spawn,rect", [
    ("right", (100, 150), (130, 150, 2, 180)),
    ("left", (160, 150), (130, 150, 2, 180)),
    ("up", (150, 100), (150, 140, 180, 2)),
    ("down", (150, 180), (150, 140, 180, 2)),
])
def test_cannot_cross_thin_walls_even_after_stall(direction, spawn, rect):
    chef = PlayerController(spawn)
    x, y, width, height = rect
    wall = arcade.SpriteSolidColor(width, height, x, y)
    walls = arcade.SpriteList()
    walls.append(wall)
    chef.set_move_key(direction, True)
    for _ in range(20):
        chef.update(1.0, walls)
        assert not arcade.check_for_collision(chef.sprite, wall)
    if direction == "right":
        assert chef.position[0] < x
    elif direction == "left":
        assert chef.position[0] > x
    elif direction == "up":
        assert chef.position[1] < y
    else:
        assert chef.position[1] > y
    assert chef.state == "idle"


def test_diagonal_slides_along_wall():
    chef = PlayerController((100, 100))
    walls = arcade.SpriteList()
    walls.append(arcade.SpriteSolidColor(10, 600, 140, 350))
    chef.set_move_key("up", True)
    chef.set_move_key("right", True)
    for _ in range(60):
        chef.update(1 / 60, walls)
    assert chef.position[0] < 125
    assert chef.position[1] > 230
    assert not arcade.check_for_collision_with_list(chef.sprite, walls)


@pytest.mark.parametrize("direction,axis,limit,sign", [
    ("right", 0, 900 - 24 * PLAYER_SCALE, 1),
    ("left", 0, 24 * PLAYER_SCALE, -1),
    ("up", 1, 720 - 43 * PLAYER_SCALE, 1),
    ("down", 1, 43 * PLAYER_SCALE, -1),
])
def test_kitchen_bounds_without_wall_list(direction, axis, limit, sign):
    chef = PlayerController((450, 360))
    walls = arcade.SpriteList()
    chef.set_move_key(direction, True)
    for _ in range(30):
        chef.update(0.25, walls)
    assert chef.position[axis] == pytest.approx(limit)


def test_all_target_points_are_clear_and_selectable():
    walls = walls_from_layout()
    chef = PlayerController((450, 170))
    for item in TARGETS:
        chef.reset((item.x, item.y))
        assert not arcade.check_for_collision_with_list(chef.sprite, walls)
        assert choose_target(chef.position, TARGETS) == item


def test_reset_and_invalid_time():
    chef = PlayerController((100, 100))
    walls = arcade.SpriteList()
    chef.set_move_key("up", True)
    for dt in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            chef.update(dt, walls)
    chef.reset((250, 250))
    chef.update(0.1, walls)
    assert chef.position == (250, 250)
    assert chef.direction == "down"
    assert chef.state == "idle"
    chef.update(0, walls)
    assert chef.position == (250, 250)
