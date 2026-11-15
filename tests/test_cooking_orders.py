"""Food and order invariants at the model and Arcade input boundaries."""
import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.ingredients import IngredientSystem
from restaurant.orders.system import OrderSystem
from restaurant.shared.contracts import PlateLocation, PotStage
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
    food, orders = IngredientSystem(), OrderSystem()
    orders.update(120)
    assert orders.snapshot() == ()
    assert orders.start().success
    assert not orders.start().success
    assert len(orders.snapshot()) == 1
    orders.update(8)
    assert [order.remaining_seconds for order in orders.snapshot()] == [112, 120]
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
    assert orders.try_serve(actual, food).success
    assert food.snapshot().plate.location is PlateLocation.CARRIED
    assert food.snapshot().plate.ingredients == ()
    assert not orders.try_serve(actual, food).success
    assert orders.stats().score == 150
    assert orders.stats().completed == 1
    assert orders.snapshot()[0].order_id == 2
    food.return_plate()
    food.collect("noodles")
    food.add_to_plate()
    food.pickup_plate()
    before = food.snapshot()
    assert not orders.try_serve(before.plate, food).success
    assert food.snapshot() == before
    assert orders.stats().score == 150


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


def test_expiry_replaces_orders_before_queued_service(view):
    station(view, "serve")
    for food in ("sandwich", "tomato"):
        station(view, f"box_{food}")
        station(view, "plate")
    station(view, "plate")
    before = view.ingredients.snapshot()
    station(view, "serve", dt=120)
    assert view.orders.stats().expired == 1
    assert view.orders.stats().completed == 0
    assert view.ingredients.snapshot() == before
    assert tuple(order.order_id for order in view.orders.snapshot()) == (2, 3)


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

    def play(sound, volume, loop=False):
        token = object()
        if loop:
            started.append(token)
        return token

    monkeypatch.setattr(arcade, "play_sound", play)
    monkeypatch.setattr(arcade, "stop_sound", stopped.append)
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
    assert view.orders.snapshot() == OrderSystem().snapshot()


@pytest.mark.parametrize(("elapsed", "expected"), [(30, 150), (30.01, 100)])
def test_fast_bonus_boundary_and_fresh_replacement(elapsed, expected):
    food, orders = IngredientSystem(), OrderSystem()
    food.pickup_plate()
    food.collect("sandwich")
    food.collect("tomato")
    assert not orders.try_serve(food.snapshot().plate, food).success
    assert orders.start().success
    orders.update(elapsed)
    assert orders.try_serve(food.snapshot().plate, food).success
    assert orders.stats().score == expected
    assert len(orders.snapshot()) == 2
    orders.update(7)
    assert len(orders.snapshot()) == 2
    orders.update(1)
    assert len(orders.snapshot()) == 3
    assert orders.snapshot()[-1].order_id == 4
    assert orders.snapshot()[-1].remaining_seconds == 120


def test_sandwich_and_milk_can_be_served_by_hand(view):
    station(view, "serve")
    station(view, "box_sandwich")
    before = view.ingredients.snapshot()
    station(view, "serve")
    assert view.ingredients.snapshot() == before  # Tomato sandwich needs both items.
    view.on_update(16)
    station(view, "serve")
    assert "Served #3: Sandwich" in view.message
    assert view.ingredients.snapshot().held is None
    assert view.ingredients.snapshot().plate == before.plate
    view.on_update(8)
    station(view, "box_milk")
    station(view, "serve")
    assert "Served #4: Milk" in view.message
    station(view, "serve")
    assert view.orders.stats().completed == 2
    assert view.orders.stats().score == 300
