"""Food and order invariants at the model and Arcade input boundaries."""
import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.ingredients import IngredientSystem
from restaurant.orders.models import DayRules
from restaurant.orders.system import OrderSystem
from restaurant.shared.contracts import PlateLocation, PotStage

SANDWICH_ONLY = DayRules(target_gold=10_000, recipe_ids=("tomato_sandwich",))
from restaurant.shared.settings import TARGETS


@pytest.fixture(autouse=True)
def fixed_arrival(monkeypatch):
    monkeypatch.setattr("restaurant.orders.system.Random.uniform", lambda self, low, high: 8.0)


def test_pot_recipe_rejects_invalid_and_duplicate_deposits_without_losing_food():
    food = IngredientSystem()
    for raw in ("sandwich",):
        food.collect(raw)
        before = food.snapshot()
        assert not food.add_to_pot().success
        assert food.snapshot() == before
        food.discard()
    food.collect("milk")
    assert food.add_to_pot().success
    assert food.snapshot().pot.stage is PotStage.LOADING
    food.collect("milk")
    before = food.snapshot()
    assert not food.add_to_pot().success
    assert food.snapshot() == before
    food.discard()
    food.collect("noodles")
    assert food.add_to_pot().success
    assert food.snapshot().pot.stage is PotStage.LOADING
    food.collect("tomato")
    assert food.add_to_pot().success
    assert food.snapshot().pot.remaining_seconds == 4
    food.update(3.75)
    assert food.snapshot().pot.stage is PotStage.COOKING
    food.update(0.25)
    assert food.snapshot().pot.stage is PotStage.READY
    food.collect("tomato")
    before = food.snapshot()
    assert not food.take_cooked_portion().success
    assert food.snapshot() == before
    food.discard()
    before = food.snapshot()
    assert not food.take_cooked_portion().success
    assert food.snapshot() == before
    assert food.pickup_plate().success
    assert food.take_cooked_portion().success
    assert food.snapshot().held is None
    assert food.snapshot().pot.stage is PotStage.EMPTY
    assert food.snapshot().plate.ingredients == ("pasta",)
    with pytest.raises(ValueError):
        food.collect("pasta")


def test_nonempty_docked_plate_preserves_ready_pasta():
    food = IngredientSystem()
    food.collect("sandwich")
    food.add_to_plate()
    for raw in ("noodles", "milk", "tomato"):
        food.collect(raw)
        food.add_to_pot()
    food.update(4)
    before = food.snapshot()
    assert not food.take_cooked_portion().success
    assert food.snapshot() == before


def test_wrong_quantity_stale_revision_and_repeat_serving():
    food, orders = IngredientSystem(), OrderSystem(rules=SANDWICH_ONLY)
    assert [(o.order_id, o.remaining_seconds) for o in orders.snapshot()] == [(1, 90)]
    orders.update(8)                         # timers run from arrival; the next customer comes in
    assert [(o.order_id, o.remaining_seconds) for o in orders.snapshot()] == [(1, 82), (2, 90)]
    for raw in ("tomato", "sandwich", "tomato"):
        food.collect(raw)
        food.add_to_plate()
    assert food.pickup_plate().success
    wrong = food.snapshot()
    assert not orders.try_serve(wrong.plate, food).success
    assert not food.remove_from_plate().success
    assert food.snapshot() == wrong
    assert orders.stats().score == 0
    assert food.return_plate().success
    assert food.snapshot().plate.ingredients == wrong.plate.ingredients
    food.remove_from_plate()
    assert not food.pickup_plate().success
    food.discard()
    food.pickup_plate()
    stale = food.snapshot().plate
    food.return_plate()
    food.pickup_plate()
    assert not orders.try_serve(stale, food).success
    actual = food.snapshot().plate
    paid = orders.snapshot()[0].reward
    assert orders.try_serve(actual, food).success
    assert food.snapshot().plate.location is PlateLocation.CARRIED
    assert food.snapshot().plate.ingredients == ()
    assert not orders.try_serve(actual, food).success
    assert orders.stats().score == paid == 60 + int(30 * 82 / 90)
    assert orders.stats().completed == 1
    assert orders.snapshot()[0].order_id == 2
    food.return_plate()
    food.collect("noodles")
    food.add_to_plate()
    food.pickup_plate()
    before = food.snapshot()
    assert not orders.try_serve(before.plate, food).success
    assert food.snapshot() == before
    assert orders.stats().score == paid


@pytest.fixture
def view():
    window = create_window(visible=False)
    try:
        window.current_view.audio.muted = True
        yield window.current_view
    finally:
        window.close()


def press(view, key, dt=0):
    view.on_key_press(key, 0)
    view.on_update(dt)
    view.on_key_release(key, 0)


def station(view, target_id, dt=0):
    target = next(item for item in TARGETS if item.target_id == target_id)
    view.player.reset((target.x, target.y))
    press(view, arcade.key.E, dt)


def test_expiry_replaces_orders_before_queued_service(view, monkeypatch):
    # Nobody else arrives while this order runs out.
    monkeypatch.setattr("restaurant.orders.system.Random.uniform", lambda self, low, high: 500.0)
    view.orders.reset(rules=DayRules(target_gold=10_000, recipe_ids=("tomato_sandwich",)))
    for food in ("sandwich", "tomato"):
        station(view, f"box_{food}")
        station(view, "plate")
    station(view, "plate")
    before = view.ingredients.snapshot()
    station(view, "serve", dt=91)            # the order runs out in the same frame
    assert view.orders.stats().expired == 1
    assert view.orders.stats().completed == 0
    assert view.ingredients.snapshot() == before
    view.on_update(2)                        # the next customer arrives soon after
    assert tuple(order.order_id for order in view.orders.snapshot()) == (2,)


def test_carried_plate_collects_and_cooks_through_station_inputs(view):
    station(view, "plate")
    for item in ("noodles", "milk", "tomato", "noodles"):
        station(view, f"box_{item}")
    before = view.ingredients.snapshot()
    station(view, "box_sandwich")
    assert view.ingredients.snapshot() == before
    assert "full" in view.message.lower()
    station(view, "pot")
    state = view.ingredients.snapshot()
    assert state.held is None and state.plate.location is PlateLocation.CARRIED
    assert state.plate.ingredients == ("noodles",)
    assert state.pot.ingredients == ("noodles", "milk", "tomato")
    before = state
    station(view, "pot")
    assert view.ingredients.snapshot() == before
    view.on_update(4)
    station(view, "box_milk")
    station(view, "box_tomato")
    station(view, "box_sandwich")
    before = view.ingredients.snapshot()
    station(view, "pot")
    assert view.ingredients.snapshot() == before
    assert before.pot.stage is PotStage.READY
    station(view, "bin")
    assert view.ingredients.snapshot().plate.location is PlateLocation.CARRIED
    assert view.ingredients.snapshot().plate.ingredients == ()
    station(view, "pot")
    state = view.ingredients.snapshot()
    assert state.plate.ingredients == ("pasta",)
    station(view, "box_tomato")
    assert view.ingredients.snapshot() == state
    assert state.pot.stage is PotStage.EMPTY


def test_audio_loop_lifecycle_pause_mute_ready_reset_and_hide(view, monkeypatch):
    started, stopped = [], []

    def stop(token):
        if token in started:                 # count the bubble loop, not the music
            stopped.append(token)

    def play(sound, volume, loop=False):
        token = object()
        if loop and sound is view.audio._sounds["bubble"]:
            started.append(token)
        return token

    monkeypatch.setattr(arcade, "play_sound", play)
    monkeypatch.setattr(arcade, "stop_sound", stop)
    press(view, arcade.key.M)
    station(view, "serve")
    for food in ("noodles", "milk", "tomato"):
        station(view, f"box_{food}")
        station(view, "pot")
    view.on_update(0.5)
    assert len(started) == 1
    before = view.ingredients.snapshot(), view.orders.snapshot()
    press(view, arcade.key.P)
    view.on_update(20)
    assert (view.ingredients.snapshot(), view.orders.snapshot()) == before
    assert stopped == started
    press(view, arcade.key.P)
    assert len(started) == 2
    press(view, arcade.key.M)
    assert stopped == started
    press(view, arcade.key.M)
    assert len(started) == 3
    view.on_hide_view()
    assert stopped == started
    view.on_update(0)
    assert len(started) == 4
    view.on_update(3.5)
    assert stopped == started
    assert view.ingredients.snapshot().pot.stage is PotStage.READY
    station(view, "plate")
    station(view, "pot")
    station(view, "bin")
    station(view, "plate")
    for food in ("noodles", "milk", "tomato"):
        station(view, f"box_{food}")
        station(view, "pot")
    assert len(started) == 5
    press(view, arcade.key.R)
    assert stopped == started
    press(view, arcade.key.M)
    press(view, arcade.key.R)
    assert view.audio.muted
    assert view.ingredients.snapshot() == IngredientSystem().snapshot()
    (fresh,) = view.orders.snapshot()        # a new day: the first order, no gold
    assert fresh.order_id == 1 and fresh.remaining_seconds == fresh.patience_seconds
    stats = view.orders.stats()
    assert (stats.accepted, stats.completed, stats.expired, stats.score) == (1, 0, 0, 0)


@pytest.mark.parametrize("elapsed", [0, 30, 60, 89])
def test_speed_tip_shrinks_and_fresh_orders_arrive(elapsed):
    food, orders = IngredientSystem(), OrderSystem(rules=SANDWICH_ONLY)
    food.pickup_plate()
    food.collect("sandwich")
    food.collect("tomato")
    orders.update(elapsed)                   # the first order's timer has been running
    assert orders.try_serve(food.snapshot().plate, food).success
    assert orders.stats().score == 60 + int(30 * (90 - elapsed) / 90)
    assert all(order.remaining_seconds <= 90 for order in orders.snapshot())
    for _ in range(30):
        orders.update(8)
        assert len(orders.snapshot()) <= 3                             # never more than three
    assert orders.stats().expired > 0                                  # ignored orders run out
    assert [o.order_id for o in orders.snapshot()] == sorted(o.order_id for o in orders.snapshot())


def test_sandwich_and_milk_can_be_served_by_hand(view):
    view.orders.reset(rules=DayRules(target_gold=10_000, recipe_ids=("sandwich", "milk")))
    view.orders.drain_events()
    first = view.orders.snapshot()[0]
    station(view, "box_tomato")
    before = view.ingredients.snapshot()
    station(view, "serve")                   # a tomato is not served by hand
    assert "Bring a plate" in view.message
    assert view.ingredients.snapshot() == before
    station(view, "bin")
    station(view, f"box_{first.required[0]}")
    station(view, "serve")
    assert f"Served #{first.order_id}: {first.recipe_name}" in view.message
    assert view.ingredients.snapshot().held is None
    assert view.ingredients.snapshot().plate == before.plate
    view.on_update(2)                        # the next customer
    second = view.orders.snapshot()[0]
    station(view, f"box_{second.required[0]}")
    station(view, "serve")
    assert f"Served #{second.order_id}" in view.message
    station(view, "serve")                   # nothing in hand
    assert view.orders.stats().completed == 2
    assert view.orders.stats().score == view.total_gold > 0
