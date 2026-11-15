"""Orders inside the real game: key presses -> systems -> effects, sound, days.

The promises: orders are live with their timer running the moment they
arrive, a correct plate pays exactly once and the chef keeps the empty plate,
a wrong plate changes nothing, expiry beats a same-frame serve, pause freezes
timers, finishing a day needs the plate returned, then Enter opens the next
kitchen.
"""
import arcade
import pytest

from restaurant.game_view import FADE_SECONDS, create_window
from restaurant.kitchen.days import DAYS
from restaurant.orders.models import DayRules
from restaurant.shared.contracts import PlateLocation


@pytest.fixture(scope="module")
def window():
    window = create_window(visible=False, seed=11)
    yield window
    window.close()


@pytest.fixture
def view(window):
    view = window.current_view
    view.reset()
    view.audio.history.clear()
    return view


def fix_menu(view, *recipe_ids, target=10_000, arrival=10.0):
    view.orders.reset(rules=DayRules(target_gold=target, arrival_seconds=arrival, recipe_ids=recipe_ids))
    view.sidebar.reset()


def tap(view, key):
    view.on_key_press(key, 0)
    view.on_key_release(key, 0)


def use(view, target_id, key=arcade.key.E):
    target = next(t for t in view.targets if t.target_id == target_id)
    view.player.reset((target.x, target.y))
    view.on_key_press(key, 0)
    view.on_update(1 / 60)
    view.on_key_release(key, 0)


def orders(view):
    return list(view.orders.snapshot())


def carry(view, *foods):
    if view.ingredients.snapshot().plate.location is not PlateLocation.CARRIED:
        use(view, "plate")
    for food in foods:
        use(view, f"box_{food}")


def test_an_order_arrives_live_with_a_bell_and_its_timer_already_running(view):
    view.on_update(1 / 60)
    assert "order_bell" in view.audio.history
    assert view.effects.call_time > 0                    # the "!" over the hatch
    (order,) = orders(view)
    assert order.status == "accepted" and view.orders.stats().accepted == 1
    view.on_update(2.0)
    assert orders(view)[0].remaining_seconds == pytest.approx(order.remaining_seconds - 2.0)
    view.audio.history.clear()
    use(view, "serve")                                   # empty hands: nothing to serve
    assert "Bring a plate" in view.message and "reject" in view.audio.history
    assert view.orders.stats().completed == 0


def test_correct_plate_pays_once_and_the_chef_keeps_the_empty_plate(view):
    fix_menu(view, "lunch_set")
    order = orders(view)[0]
    carry(view, "milk", "sandwich")                      # placement order is irrelevant
    use(view, "serve")
    stats = view.orders.stats()
    paid = stats.score
    assert stats.completed == 1 and order.reward - 2 <= paid <= order.reward
    plate = view.ingredients.snapshot().plate
    assert plate.ingredients == () and plate.location is PlateLocation.CARRIED
    assert view.total_gold == paid
    assert {"serve_success", "coin"} <= set(view.audio.history)
    assert any(p.kind == "coin" for p in view.effects.particles)
    assert f"+{paid} G" in [text.value for text in view.effects.texts]
    for _ in range(3):                                   # repeated presses never pay twice
        use(view, "serve")
    assert view.orders.stats().completed == 1 and view.orders.stats().score == paid


def test_wrong_plate_is_sent_back_and_changes_nothing(view):
    fix_menu(view, "pasta")
    carry(view, "noodles", "milk")                       # raw food is not pasta
    view.audio.history.clear()
    tickets = lambda: [(o.order_id, o.status) for o in view.orders.snapshot()]  # noqa: E731
    before = tickets(), view.orders.stats(), view.ingredients.snapshot()
    use(view, "serve")                                   # (one frame of time passes)
    assert (tickets(), view.orders.stats(), view.ingredients.snapshot()) == before
    assert "serve_fail" in view.audio.history and "serve_success" not in view.audio.history
    assert "sent it back" in view.message
    assert view.effects.shake_time > 0 and view.effects.flash > 0
    view.on_draw()
    assert view.shake != (0.0, 0.0)                      # the camera really moves


def test_an_order_that_expires_this_frame_cannot_be_served(view):
    fix_menu(view, "tomato_sandwich", arrival=500.0)      # no one else arrives meanwhile
    carry(view, "sandwich", "tomato")
    first = orders(view)[0]
    remaining = first.remaining_seconds
    target = next(t for t in view.targets if t.target_id == "serve")
    view.player.reset((target.x, target.y))
    view.audio.history.clear()
    view.on_key_press(arcade.key.E, 0)
    view.on_update(remaining + 0.01)                     # timer and key land in one frame
    view.on_key_release(arcade.key.E, 0)
    stats = view.orders.stats()
    assert stats.expired >= 1 and stats.score == 0
    assert first.order_id not in {o.order_id for o in orders(view)}
    assert "order_expired" in view.audio.history and "serve_success" not in view.audio.history
    assert sorted(view.ingredients.snapshot().plate.ingredients) == ["sandwich", "tomato"]


def test_low_time_ticks_once_per_second(view):
    view.on_update(orders(view)[0].remaining_seconds - 9.5)
    view.audio.history.clear()
    for _ in range(180):                                 # three seconds
        view.on_update(1 / 60)
    assert 3 <= list(view.audio.history).count("timer_tick") <= 4


def test_pause_freezes_timers_and_restart_begins_day_one(view):
    before = view.orders.snapshot()
    tap(view, arcade.key.P)
    view.on_update(30.0)
    use(view, "serve")
    assert view.orders.snapshot() == before
    tap(view, arcade.key.P)
    view.on_update(1.0)
    assert view.orders.snapshot()[0].remaining_seconds == pytest.approx(before[0].remaining_seconds - 1.0)
    tap(view, arcade.key.R)
    stats = view.orders.stats()
    assert (stats.accepted, stats.completed, stats.score) == (1, 0, 0) and view.day_index == 0


def test_reaching_the_target_ends_the_day_then_the_plate_goes_home_then_enter(view):
    fix_menu(view, "pasta", target=200)
    while not view.day_complete:
        carry(view)
        for food in ("noodles", "milk", "tomato"):
            use(view, f"box_{food}")
        use(view, "pot")
        view.on_update(4.5)
        use(view, "pot")
        use(view, "serve")
    gold = view.orders.stats().score
    assert gold >= 200 and view.total_gold == gold
    assert "day_complete" in view.audio.history
    assert any(p.kind == "confetti" for p in view.effects.particles)
    view.on_draw()
    frozen = view.orders.stats()
    view.on_update(300.0)                                # no expiries, no new tickets
    use(view, "serve")
    assert view.orders.stats() == frozen
    tap(view, arcade.key.ENTER)                          # still carrying the plate
    assert view.day_index == 0 and "Return" in view.message
    use(view, "plate")
    tap(view, arcade.key.ENTER)
    assert view.day_index == 1 and view.day.map_id == "warm_clean"
    assert view.fade == pytest.approx(FADE_SECONDS) and "transition" in view.audio.history
    view.on_draw()
    assert view.orders.stats().score == 0 and view.orders.stats().target == DAYS[1].rules.target_gold
    assert view.total_gold == gold                       # gold carries across days


def test_number_keys_jump_to_any_day_with_its_music(view):
    tap(view, arcade.key.KEY_3)
    assert view.day_index == 2 and view.day.map_id == "metal_damaged"
    assert view.audio.music_name == "bgm_metal"
    tap(view, arcade.key.KEY_1)
    assert view.day_index == 0 and view.audio.music_name == "bgm_warm"


def test_mute_survives_a_restart(view):
    muted = view.audio.muted
    tap(view, arcade.key.M)
    tap(view, arcade.key.R)
    assert view.audio.muted is not muted
    tap(view, arcade.key.M)
    assert view.audio.muted is muted


def test_drawing_never_changes_game_state(view):
    carry(view, "sandwich")
    snapshot = view.orders.snapshot(), view.orders.stats(), view.ingredients.snapshot()
    for _ in range(3):
        view.on_draw()
    assert (view.orders.snapshot(), view.orders.stats(), view.ingredients.snapshot()) == snapshot
