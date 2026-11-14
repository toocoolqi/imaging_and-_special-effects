"""Map checks: artwork, solid furniture, safe paths, and the reserved chop hook."""
from collections import deque
from math import isfinite

import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.kitchen.layout import PROPS, ROOM_SOLIDS, SOLID_PROPS
from restaurant.kitchen.scene import load_textures
from restaurant.player.controller import (
    FOOT_HALF_HEIGHT, FOOT_HALF_WIDTH, FOOT_OFFSET_Y, PlayerController,
)
from restaurant.shared.contracts import InteractionTarget
from restaurant.shared.settings import (
    KITCHEN_HEIGHT, KITCHEN_WIDTH, PLAYER_SCALE, SPAWN, TARGETS, WALL_RECTANGLES,
)

HALF_WIDTH = FOOT_HALF_WIDTH * PLAYER_SCALE
HALF_HEIGHT = FOOT_HALF_HEIGHT * PLAYER_SCALE
OFFSET_Y = FOOT_OFFSET_Y * PLAYER_SCALE


def clear_center(point, margin=0.5):
    """Expand furniture by the feet; translate sprite centers to ground space."""
    x, y = point
    y += OFFSET_Y
    if not (HALF_WIDTH <= x <= KITCHEN_WIDTH - HALF_WIDTH and
            HALF_HEIGHT <= y <= KITCHEN_HEIGHT - HALF_HEIGHT):
        return False
    return not any(
        abs(x - cx) <= width / 2 + HALF_WIDTH + margin and
        abs(y - cy) <= height / 2 + HALF_HEIGHT + margin
        for cx, cy, width, height in WALL_RECTANGLES
    )


def clear_segment(start, end):
    # Grid edges are axis-aligned. Their bounding box must not intersect an
    # expanded obstacle, including any thin rectangle between two clear nodes.
    left, right = sorted((start[0], end[0]))
    bottom, top = sorted((start[1], end[1]))
    bottom, top = bottom + OFFSET_Y, top + OFFSET_Y
    return not any(
        left <= cx + width / 2 + HALF_WIDTH + 0.5 and
        right >= cx - width / 2 - HALF_WIDTH - 0.5 and
        bottom <= cy + height / 2 + HALF_HEIGHT + 0.5 and
        top >= cy - height / 2 - HALF_HEIGHT - 0.5
        for cx, cy, width, height in WALL_RECTANGLES
    )


def test_artwork_and_supports_match_solid_furniture():
    props = {prop.prop_id: prop for prop in PROPS}
    assert len(props) == len(PROPS)
    assert WALL_RECTANGLES == ROOM_SOLIDS + tuple(prop.collision_rectangle for prop in SOLID_PROPS)
    for name, texture in load_textures().items():
        image = texture.image
        assert image.width > 0 and image.height > 0
        assert image.getbbox() is not None, name
    for prop in PROPS:
        assert all(map(isfinite, prop.rectangle))
        assert prop.width > 0 and prop.height > 0
        assert 0 <= prop.x - prop.width / 2 < prop.x + prop.width / 2 <= KITCHEN_WIDTH
        assert 0 <= prop.y - prop.height / 2 < prop.y + prop.height / 2 <= KITCHEN_HEIGHT
        if prop.support is None:
            assert prop.solid, f"Floor object {prop.prop_id} needs collision"
            dx, dy, width, height = prop.footprint
            assert abs(dx) + width / 2 <= prop.width / 2
            assert abs(dy) + height / 2 <= prop.height / 2
        else:
            support = props[prop.support]
            assert not prop.solid and support.solid
            assert abs(prop.x - support.x) + prop.width / 2 <= support.width / 2
            assert abs(prop.y - support.y) + prop.height / 2 <= support.height / 2


def test_all_stations_share_a_navigable_area_with_spawn():
    # Add exact station/spawn axes to a 10px grid: the proof reaches the actual
    # points, not an arbitrary nearby cell or a point across a wall.
    assert clear_center(SPAWN)
    assert len({item.target_id for item in TARGETS}) == len(TARGETS)
    xs = sorted(set(range(0, KITCHEN_WIDTH + 1, 10)) | {SPAWN[0]} |
                {item.x for item in TARGETS})
    ys = sorted(set(range(0, KITCHEN_HEIGHT + 1, 10)) | {SPAWN[1]} |
                {item.y for item in TARGETS})
    free = {(ix, iy) for ix, x in enumerate(xs) for iy, y in enumerate(ys)
            if clear_center((x, y))}
    origin = (xs.index(SPAWN[0]), ys.index(SPAWN[1]))
    visited, queue = {origin}, deque([origin])
    while queue:
        ix, iy = queue.popleft()
        for node in ((ix - 1, iy), (ix + 1, iy), (ix, iy - 1), (ix, iy + 1)):
            if node in free and node not in visited:
                if clear_segment((xs[ix], ys[iy]), (xs[node[0]], ys[node[1]])):
                    visited.add(node)
                    queue.append(node)
    for item in TARGETS:
        assert clear_center((item.x, item.y)), item.target_id
        assert (xs.index(item.x), ys.index(item.y)) in visited, item.target_id


@pytest.mark.parametrize("rectangle", WALL_RECTANGLES)
def test_each_obstacle_blocks_its_accessible_sides(rectangle):
    walls = arcade.SpriteList(use_spatial_hash=True)
    for cx, cy, width, height in WALL_RECTANGLES:
        walls.append(arcade.SpriteSolidColor(width, height, cx, cy))
    cx, cy, width, height = rectangle
    chef = PlayerController(SPAWN)
    checked = 0
    # Slight clearance permits narrow but valid gaps between neighboring crates.
    for direction, axis, side, half_extent, chef_half in (
        ("right", 0, -1, width / 2, HALF_WIDTH),
        ("left", 0, 1, width / 2, HALF_WIDTH),
        ("up", 1, -1, height / 2, HALF_HEIGHT),
        ("down", 1, 1, height / 2, HALF_HEIGHT),
    ):
        # A long wall's midpoint can be obstructed by furniture. Sample its
        # other accessible face sections too, instead of declaring it untested.
        for fraction in (-0.25, 0, 0.25):
            start = [cx, cy]
            start[axis] += side * (half_extent + chef_half + 1.5)
            start[1 - axis] += fraction * (height if axis == 0 else width)
            start[1] -= OFFSET_Y
            if not clear_center(start):
                continue
            chef.reset(tuple(start))
            chef.set_move_key(direction, True)
            for _ in range(6):
                chef.update(1.0, walls)
                assert not arcade.check_for_collision_with_list(chef.sprite, walls)
                assert side * (chef.ground_position[axis] - (cx, cy)[axis]) >= half_extent + chef_half - 0.1
            assert chef.state == "idle"
            checked += 1
    assert checked, f"No clear approach tested for obstacle {rectangle}"


def test_chopping_station_is_a_feedback_hook_only():
    chopping = next(item for item in TARGETS if item.kind == "chop")
    assert InteractionTarget("future_chop", "chop", chopping.x, chopping.y).ingredient_id is None
    with pytest.raises(ValueError, match="Only box"):
        InteractionTarget("bad_chop", "chop", chopping.x, chopping.y, "tomato")
    window = create_window(visible=False)
    try:
        view = window.current_view
        view.player.reset((chopping.x, chopping.y))
        before, targets = view.player.position, view.targets
        view.on_key_press(arcade.key.E, 0)
        view.on_key_press(arcade.key.E, 0)
        view.on_update(1 / 60)
        assert view.selected == chopping
        assert view.interaction_count == 1
        assert "Cutting" in view.message
        assert view.player.position == before and view.player.state == "idle"
        assert view.targets == targets
        view.on_key_release(arcade.key.E, 0)
        view.on_key_press(arcade.key.Q, 0)
        view.on_update(1 / 60)
        assert view.interaction_count == 1
        assert "plate" in view.message.lower()
    finally:
        window.close()


def test_chef_can_reach_counter_edge_and_is_occluded_only_when_behind():
    window = create_window(visible=False)
    try:
        view = window.current_view
        prop = next(p for p in PROPS if p.prop_id == "plate_counter")
        _, base_y, _, base_h = prop.collision_rectangle
        front_edge = base_y - base_h / 2
        target = next(t for t in TARGETS if t.kind == "plate")
        view.player.reset((target.x, target.y))
        view.player.set_move_key("up", True)
        for _ in range(20):
            view.player.update(0.25, view.walls)
        foot_y = view.player.ground_position[1]
        assert 0 <= front_edge - (foot_y + HALF_HEIGHT) < 2
        # The body can overlap the raised front, without feet entering it.
        assert view.player.sprite.center_y + 46 > front_edge + 40
        assert not arcade.check_for_collision_with_list(view.player.sprite, view.walls)
        order = view.kitchen.draw_order(foot_y)
        assert order.index("plate_counter") < order.index("player")
        behind_y = base_y + base_h / 2 + HALF_HEIGHT + 2
        view.player.reset((prop.x, behind_y - OFFSET_Y))
        assert not arcade.check_for_collision_with_list(view.player.sprite, view.walls)
        order = view.kitchen.draw_order(behind_y)
        assert order.index("player") < order.index("plate_counter")
        view.on_draw()
    finally:
        window.close()


def test_service_hatch_uses_existing_serve_hook():
    window = create_window(visible=False)
    try:
        view = window.current_view
        target = next(t for t in TARGETS if t.kind == "serve")
        view.player.reset((target.x, target.y))
        view.on_key_press(arcade.key.E, 0)
        view.on_update(1 / 60)
        assert view.selected == target
        assert view.interaction_count == 1
        assert "Service open" in view.message
        assert len(view.orders.snapshot()) == 1
    finally:
        window.close()
