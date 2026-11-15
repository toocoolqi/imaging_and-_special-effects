"""Real Arcade input/rendering integration for deadlines and enemies."""
import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.hazards.system import Blocker, Ghost, Vampire
from restaurant.kitchen.days import DAYS
from restaurant.orders.models import DayRules
from restaurant.shared.settings import PLAYER_SPEED


@pytest.fixture(scope="module")
def window():
    window = create_window(visible=False, seed=19)
    yield window
    window.close()


@pytest.fixture
def view(window):
    v = window.current_view
    v.reset()
    return v


def tap(v, key):
    v.on_key_press(key, 0)
    v.on_update(0)
    v.on_key_release(key, 0)


def test_pace_is_faster_and_shift_budgets_decrease():
    assert PLAYER_SPEED == 230
    assert [d.shift_seconds for d in DAYS] == [180, 165, 150, 135]
    assert [d.rules.patience_seconds for d in DAYS] == [82, 68, 56, 45]


def test_deadline_fails_freezes_everything_and_retries_same_day(view):
    view.total_gold = 170
    view.go_to_day(2)
    view.total_gold += 35                 # earned during this unsuccessful attempt
    view.shift_remaining = .1
    view.actions.append("interact")
    view.on_update(.1)
    assert view.failed and view.shift_remaining == 0 and not view.actions
    before = view.ingredients.snapshot(), view.orders.snapshot(), view.player.position
    view.on_update(20)
    tap(view, arcade.key.E)
    tap(view, arcade.key.P)
    assert (view.ingredients.snapshot(), view.orders.snapshot(), view.player.position) == before
    assert not view.paused
    view.on_draw()                       # fail overlay and zero-clock render
    tap(view, arcade.key.ENTER)
    assert view.day_index == 2 and not view.failed
    assert view.total_gold == 170 and view.shift_remaining == 150
    assert "shift_fail" in view.audio.history


def test_exact_deadline_beats_queued_service(view):
    view.orders.reset(rules=DayRules(target_gold=1, recipe_ids=("sandwich",)))
    view.ingredients.collect("sandwich")
    station = next(t for t in view.targets if t.kind == "serve")
    view.player.reset((station.x, station.y))
    view.shift_remaining = .05
    view.on_key_press(arcade.key.E, 0)
    view.on_update(.05)
    assert view.failed and view.orders.stats().score == 0
    assert view.ingredients.snapshot().held == "sandwich"


def test_goal_before_deadline_stops_clock_and_removes_blocker(view):
    view.orders.reset(rules=DayRules(target_gold=1, recipe_ids=("sandwich",)))
    view.ingredients.collect("sandwich")
    view.encounters.blocker = Blocker(480, 330, "blocking", 11)
    view.sync_blocker()
    assert view._blocker_wall in view.walls
    station = next(t for t in view.targets if t.kind == "serve")
    view.player.reset((station.x, station.y))
    view.shift_remaining = .1
    tap(view, arcade.key.E)
    assert view.day_complete and not view.failed
    view.on_update(10)
    assert view.shift_remaining == .1 and not view.failed
    assert view._blocker_wall is None and view.encounters.blocker is None


def test_pause_freezes_shift_warnings_and_stun(view):
    view.go_to_day(1)
    view.encounters.vampire = Vampire(-70, 210, 1)
    view.encounters.stun = .5
    before = view.shift_remaining, view.encounters.vampire.remaining, view.encounters.stun
    tap(view, arcade.key.P)
    view.on_update(30)
    assert (view.shift_remaining, view.encounters.vampire.remaining, view.encounters.stun) == before
    tap(view, arcade.key.P)
    view.on_update(.1)
    assert view.shift_remaining < before[0]


def test_e_reclaims_ghost_food_instead_of_using_station_twice(view):
    station = next(t for t in view.targets if t.kind == "plate")
    view.player.reset((station.x, station.y))
    view.ingredients.collect("tomato")
    view.ingredients.add_to_plate()
    payload = view.ingredients.steal_docked_food()
    x, y = view.player.ground_position
    view.encounters.ghost = Ghost(x, y, "flee", .65, payload)
    tap(view, arcade.key.E)
    state = view.ingredients.snapshot()
    assert state.plate.ingredients == ("tomato",)
    assert state.plate.location.value == "docked"     # E did not also pick up plate
    assert view.encounters.ghost is None
    view.on_draw()


def test_stun_blocks_actions_and_movement_then_resumes_held_key(view):
    view.player.reset((480, 250))
    view.on_key_press(arcade.key.D, 0)
    view.encounters.stun = .5
    before = view.player.position
    view.on_update(.1)
    tap(view, arcade.key.E)
    assert view.player.position == before and not view.actions
    view.on_draw()                       # orbiting stars
    view.on_update(.45)
    assert view.player.position[0] > before[0]
    view.on_key_release(arcade.key.D, 0)


def test_blocker_really_collides_then_day_reset_removes_it(view):
    view.go_to_day(2)
    view.player.reset((480, 300))         # feet at 268, blocker bottom 314
    view.encounters.blocker = Blocker(480, 330, "blocking", 11)
    view.sync_blocker()
    view.on_key_press(arcade.key.W, 0)
    for _ in range(20):
        view.on_update(.03)
    assert view.player.ground_position[1] <= 304
    assert not arcade.check_for_collision_with_list(view.player.sprite, view.walls)
    view.on_draw()
    view.go_to_day(0)
    assert view._blocker_wall is None and view.encounters.blocker is None
    assert len(view.walls) == len(view.day.walls)


@pytest.mark.parametrize("direction", [-1, 1])
def test_vampire_drawing_both_directions_and_ghost_food(view, direction):
    view.encounters.vampire = Vampire(200, 210, direction, "sweep", 0)
    view.encounters.ghost = Ghost(700, 319, "flee", .5, ("milk", "sandwich"))
    view.on_draw()


def test_frame_time_validation(view):
    for value in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            view.on_update(value)
