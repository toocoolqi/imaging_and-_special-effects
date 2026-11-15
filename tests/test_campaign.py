"""Exercise all four days through the same key events used by a player."""
import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.ingredients.chopping import CHOP_SECONDS
from restaurant.shared.contracts import PlateLocation, PotStage


@pytest.fixture(autouse=True)
def fixed_order_arrival(monkeypatch):
    monkeypatch.setattr("restaurant.orders.system.Random.uniform", lambda self, low, high: 8.0)


def use(view, target_id):
    target = next(target for target in view.targets if target.target_id == target_id)
    view.player.reset((target.x, target.y))
    assert not arcade.check_for_collision_with_list(view.player.sprite, view.walls)
    press(view, arcade.key.E)


def press(view, key):
    view.on_key_press(key, 0)
    view.on_update(0)
    view.on_key_release(key, 0)


def complete_day(view, *, check_rejection=False):
    use(view, "serve")
    use(view, "plate")
    use(view, "box_tomato")
    if check_rejection:
        before = view.ingredients.snapshot()
        use(view, "serve")
        assert view.ingredients.snapshot() == before
        assert view.orders.stats().score == 0
    use(view, "chopping_board")
    view.on_update(CHOP_SECONDS / 2)
    view.on_draw()
    assert view.chopping.state == "chopping"
    assert view.ingredients.snapshot().plate.ingredients == ()
    old_position = view.player.position
    view.on_key_press(arcade.key.S, 0)
    view.on_update(CHOP_SECONDS / 4)
    view.on_key_release(arcade.key.S, 0)
    assert view.player.position == old_position
    progress = view.chopping.progress
    press(view, arcade.key.P)
    view.on_update(5)
    assert view.chopping.progress == progress
    press(view, arcade.key.P)
    view.on_update(CHOP_SECONDS)
    assert view.chopping.state == "ready"
    use(view, "chopping_board")
    assert view.ingredients.snapshot().plate.ingredients == ("chopped_tomato",)
    use(view, "box_sandwich")
    use(view, "serve")
    assert view.orders.stats().score == 150
    assert view.ingredients.snapshot().plate.location is PlateLocation.CARRIED
    assert view.ingredients.snapshot().plate.ingredients == ()
    use(view, "serve")
    assert view.orders.stats().score == 150

    for food in ("noodles", "milk", "tomato"):
        use(view, f"box_{food}")
    use(view, "pot")
    assert view.ingredients.snapshot().pot.stage is PotStage.COOKING
    press(view, arcade.key.P)
    view.on_update(5)
    assert view.ingredients.snapshot().pot.remaining_seconds == 4
    press(view, arcade.key.P)
    view.on_update(8)
    assert view.ingredients.snapshot().pot.stage is PotStage.READY
    use(view, "pot")
    assert view.ingredients.snapshot().plate.ingredients == ("pasta",)
    use(view, "serve")
    assert view.day_complete
    press(view, arcade.key.ENTER)
    assert view.ingredients.snapshot().plate.location is PlateLocation.CARRIED
    assert "Return" in view.message
    use(view, "plate")
    assert view.ingredients.snapshot().plate.location is PlateLocation.DOCKED


def test_four_day_playthrough_and_restart():
    window = create_window(visible=False)
    try:
        view = window.current_view
        for day in range(4):
            assert view.day_index == day
            complete_day(view, check_rejection=(day == 0))
            view.on_draw()
            press(view, arcade.key.ENTER)
        assert view.finished
        assert view.total_gold == 1200
        view.on_draw()
        press(view, arcade.key.R)
        assert view.day_index == view.total_gold == 0
        assert not view.finished
    finally:
        window.close()


def test_expired_ticket_preserves_plate_and_keeps_newer_orders():
    window = create_window(visible=False)
    try:
        view = window.current_view
        use(view, "serve")
        use(view, "box_sandwich")
        use(view, "plate")
        old = view.orders.snapshot()[0]
        view.on_update(121)
        assert view.orders.stats().expired == 1
        assert all(order.order_id > old.order_id for order in view.orders.snapshot())
        assert view.ingredients.snapshot().plate.ingredients == ("sandwich",)
    finally:
        window.close()
