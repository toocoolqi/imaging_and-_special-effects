"""Exercise rear access against the installed worktops in each kitchen."""
import arcade
import pytest

from restaurant.kitchen.days import DAYS
from restaurant.kitchen.layout import FLOOR_TOP
from restaurant.player.controller import (
    FOOT_HALF_HEIGHT, FOOT_HALF_WIDTH, FOOT_OFFSET_Y, PlayerController,
)
from restaurant.shared.settings import PLAYER_SCALE


@pytest.mark.parametrize("day", DAYS, ids=[day.style for day in DAYS])
def test_chef_cannot_walk_through_the_rear_of_fixed_worktops(day):
    walls = arcade.SpriteList(use_spatial_hash=True)
    for x, y, width, height in day.walls:
        walls.append(arcade.SpriteSolidColor(width, height, x, y))

    chef = PlayerController(day.spawn)
    half_width = FOOT_HALF_WIDTH * PLAYER_SCALE
    rear_lane = FLOOR_TOP - FOOT_HALF_HEIGHT * PLAYER_SCALE - 16
    sprite_y = rear_lane - FOOT_OFFSET_Y * PLAYER_SCALE

    for prop_id, side, direction in (
        ("wash_counter", 1, "left"),
        ("floor_stove", 1, "left"),
        ("serving_table", -1, "right"),
    ):
        prop = next(prop for prop in day.props if prop.prop_id == prop_id)
        x, _, width, _ = prop.collision_rectangle
        side_edge = x + side * width / 2
        chef.reset((side_edge + side * (half_width + 2), sprite_y))
        assert not arcade.check_for_collision_with_list(chef.sprite, walls)
        chef.set_move_key(direction, True)
        for _ in range(20):
            chef.update(1 / 60, walls)

        assert side * (chef.ground_position[0] - side_edge) >= half_width - 0.1
        assert not arcade.check_for_collision_with_list(chef.sprite, walls)

    for station in day.targets:
        chef.reset((station.x, station.y))
        assert not arcade.check_for_collision_with_list(chef.sprite, walls), station.target_id
