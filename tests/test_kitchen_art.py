"""The four kitchens: artwork contract, twin alignment, routes and ambience.

Run: python -m pytest tests/test_kitchen_art.py -q   (needs a desktop for Arcade)
"""
from collections import deque
import json

import arcade
from PIL import Image, ImageChops
import pytest

from restaurant.game_view import create_window
from restaurant.kitchen.days import ART_ROOT, DAYS, MAP_IDS
from restaurant.kitchen.layout import KITCHEN_HEIGHT, KITCHEN_WIDTH, WALL_ART
from restaurant.kitchen.scene import TASK2_ASSETS, KitchenScene
from restaurant.player.controller import FOOT_HALF_HEIGHT, FOOT_HALF_WIDTH, FOOT_OFFSET_Y
from restaurant.shared.settings import PLAYER_SCALE

HALF_W, HALF_H = FOOT_HALF_WIDTH * PLAYER_SCALE, FOOT_HALF_HEIGHT * PLAYER_SCALE
OFFSET_Y = FOOT_OFFSET_Y * PLAYER_SCALE
REQUIRED_IDS = {"box_sandwich", "box_tomato", "box_noodles", "box_milk",
                "plate", "plate_back", "bin", "serve", "chopping_board", "pot"}
TWINS = (("warm", "overgrown"), ("metal", "metal_damaged"))
by_style = {day.style: day for day in DAYS}


def sprite_names(day):
    names = {p.asset for p in day.props} | {name for name, *_ in WALL_ART}
    return names - set(TASK2_ASSETS)


def world_sizes(day):
    sizes = {p.asset: (p.width, p.height) for p in day.props}
    sizes.update({name: (w, h) for name, _, _, w, h in WALL_ART})
    return sizes


# ---------------------------------------------------------------- days and folders

def test_four_days_use_the_four_environment_ids_in_story_order():
    assert [day.map_id for day in DAYS] == ["warm_overgrown", "warm_clean", "metal_damaged", "metal_clean"]
    assert set(MAP_IDS.values()) == {day.map_id for day in DAYS}
    for day in DAYS:
        assert day.headline and day.story and day.music in ("bgm_warm", "bgm_metal")
        assert {target.target_id for target in day.targets} == REQUIRED_IDS

def test_every_day_is_busier_than_the_last():
    """Shorter timers, faster arrivals and a higher gold target each day,
    never more than three orders on screen."""
    rules = [day.rules for day in DAYS]
    for earlier, later in zip(rules, rules[1:]):
        assert later.patience_seconds < earlier.patience_seconds
        assert later.arrival_seconds < earlier.arrival_seconds
        assert later.target_gold > earlier.target_gold
    assert all(rule.max_cards == 3 for rule in rules)


@pytest.mark.parametrize("clean, damaged", TWINS)
def test_clean_and_damaged_twins_share_every_measurement(clean, damaged):
    a, b = by_style[clean], by_style[damaged]
    assert a.props == b.props and a.targets == b.targets and a.spawn == b.spawn
    assert a.walls == b.walls
    assert a.condition == "clean" and b.condition != "clean"


def test_every_folder_has_the_same_files_and_an_accurate_manifest():
    listings = {day.map_id: sorted(p.name for p in day.art_dir.glob("*.png")) for day in DAYS}
    assert len({tuple(names) for names in listings.values()}) == 1
    assert "room.png" in listings["warm_clean"]
    assert {f"{name}.png" for name in sprite_names(DAYS[0])} <= set(listings["warm_clean"])
    manifest = json.loads((ART_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["maps"]) == set(listings)
    for map_id, entry in manifest["maps"].items():
        assert sorted(entry["files"]) == listings[map_id]
        for name, info in entry["files"].items():
            with Image.open(ART_ROOT / map_id / name) as image:
                assert list(image.size) == info["pixels"], (map_id, name)


@pytest.mark.parametrize("day", DAYS, ids=[day.map_id for day in DAYS])
def test_art_sits_exactly_on_the_games_pixel_grid(day):
    with Image.open(day.art_dir / "room.png") as room:
        assert room.size == (KITCHEN_WIDTH // 2, KITCHEN_HEIGHT // 2) and room.mode == "RGB"
    sizes = world_sizes(day)
    for name in sprite_names(day):
        with Image.open(day.art_dir / f"{name}.png") as image:
            w, h = sizes[name]
            assert image.mode == "RGBA"
            assert image.size == (round(w / 2), round(h / 2)), name     # drawn 1:1
            alpha = image.getchannel("A")
            corners = [alpha.getpixel(xy) for xy in ((0, 0), (image.width - 1, 0), (0, image.height - 1))]
            assert max(corners) < 40, f"{name} needs a transparent background"
    for name in TASK2_ASSETS:                       # food art is never baked in
        assert not (day.art_dir / f"{name}.png").exists()


@pytest.mark.parametrize("clean, damaged", TWINS)
def test_damage_keeps_outlines_and_is_real_detail_not_a_tint(clean, damaged):
    """Same silhouette pixel for pixel; much of each object untouched and a
    visible share strongly changed. A flat tint changes everything a little."""
    for path in sorted(by_style[clean].art_dir.glob("*.png")):
        a = Image.open(path).convert("RGBA")
        b = Image.open(by_style[damaged].art_dir / path.name).convert("RGBA")
        assert a.size == b.size
        assert a.getchannel("A").tobytes() == b.getchannel("A").tobytes(), path.name
        diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L")
        solid = a.getchannel("A").point(lambda v: 255 if v > 128 else 0)
        histogram = diff.histogram(solid)
        total = sum(histogram)
        assert sum(histogram[:8]) / total > 0.10, f"{path.name} lost its original look"
        assert sum(histogram[45:]) / total > 0.015, f"{path.name} shows too little damage"


def test_silver_kitchen_furniture_really_is_steel():
    def saturation(day, name):
        image = Image.open(day.art_dir / f"{name}.png").convert("RGBA")
        solid = image.getchannel("A").point(lambda v: 255 if v > 128 else 0)
        histogram = image.convert("RGB").convert("HSV").getchannel("S").histogram(solid)
        return sum(i * n for i, n in enumerate(histogram)) / sum(histogram)
    for name in ("table", "sink", "pass_counter"):
        assert saturation(by_style["warm"], name) > 2.5 * saturation(by_style["metal"], name), name


def test_build_tool_reproduces_the_stored_files():
    from tools import build_kitchens as build
    size = build.display_sizes()["bin"]
    base = build.load_base("bin", size)
    for style, make in (("overgrown", build.overgrow),
                        ("metal_damaged", lambda n, i: build.damage_metal(n, build.metalize(n, i)))):
        stored = Image.open(by_style[style].art_dir / "bin.png").convert("RGBA")
        assert build.finish(make("bin", base)).tobytes() == stored.tobytes()


# ---------------------------------------------------------------- routes

def clear_center(day, point, margin=0.5):
    x, y = point[0], point[1] + OFFSET_Y
    if not (HALF_W <= x <= KITCHEN_WIDTH - HALF_W and HALF_H <= y <= KITCHEN_HEIGHT - HALF_H):
        return False
    return not any(abs(x - cx) <= w / 2 + HALF_W + margin and abs(y - cy) <= h / 2 + HALF_H + margin
                   for cx, cy, w, h in day.walls)


def clear_segment(day, start, end):
    left, right = sorted((start[0], end[0]))
    bottom, top = sorted((start[1] + OFFSET_Y, end[1] + OFFSET_Y))
    return not any(left <= cx + w / 2 + HALF_W + 0.5 and right >= cx - w / 2 - HALF_W - 0.5 and
                   bottom <= cy + h / 2 + HALF_H + 0.5 and top >= cy - h / 2 - HALF_H - 0.5
                   for cx, cy, w, h in day.walls)


@pytest.mark.parametrize("day", DAYS, ids=[day.map_id for day in DAYS])
def test_every_station_is_reachable_and_clear_of_puddles_and_panels(day):
    xs = sorted(set(range(0, KITCHEN_WIDTH + 1, 10)) | {day.spawn[0]} | {t.x for t in day.targets})
    ys = sorted(set(range(0, KITCHEN_HEIGHT + 1, 10)) | {day.spawn[1]} | {t.y for t in day.targets})
    free = {(i, j) for i, x in enumerate(xs) for j, y in enumerate(ys) if clear_center(day, (x, y))}
    origin = (xs.index(day.spawn[0]), ys.index(day.spawn[1]))
    seen, queue = {origin}, deque([origin])
    while queue:
        i, j = queue.popleft()
        for node in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if node in free and node not in seen and clear_segment(day, (xs[i], ys[j]), (xs[node[0]], ys[node[1]])):
                seen.add(node)
                queue.append(node)
    for target in day.targets:
        assert (xs.index(target.x), ys.index(target.y)) in seen, target.target_id
        for px, py in day.effect_points:
            assert abs(target.x - px) > 40 or abs(target.y - 32 - py) > 24, target.target_id


# ---------------------------------------------------------------- in the game

@pytest.fixture(scope="module")
def window():
    window = create_window(visible=False, seed=3)
    yield window
    window.close()


@pytest.mark.parametrize("index", range(4))
def test_each_day_draws_its_own_room_and_furniture(window, index):
    view = window.current_view
    view.go_to_day(index)
    day = DAYS[index]
    scene = view.kitchen
    assert isinstance(scene, KitchenScene) and scene.room is not None
    expected = arcade.load_texture(day.art_dir / "table.png")
    assert scene.textures["table"].image.tobytes() == expected.image.tobytes()
    view.debug = True
    view.on_draw()
    view.debug = False


@pytest.mark.parametrize("index, cue", ((0, "drip"), (2, "spark")))
def test_damaged_rooms_have_living_ambience_with_sound(window, index, cue):
    view = window.current_view
    view.go_to_day(index)
    view.audio.history.clear()
    for _ in range(600):                                  # ten seconds of play
        view.on_update(1 / 60)
    view.on_draw()
    assert cue in view.audio.history


def test_ambience_freezes_with_pause(window):
    view = window.current_view
    view.go_to_day(0)
    view.on_key_press(arcade.key.P, 0)
    before = view.ambience.elapsed
    view.on_update(5.0)
    assert view.ambience.elapsed == before
    view.on_key_release(arcade.key.P, 0)
    view.on_key_press(arcade.key.P, 0)
    view.on_key_release(arcade.key.P, 0)
