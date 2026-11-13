"""Exercise all four days through the same key events used by a player."""
import arcade
from restaurant.game_view import create_window


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
    use(view, "box_tomato")
    use(view, "plate")
    if check_rejection:
        use(view, "plate")
        before = view.ingredients.snapshot()
        use(view, "serve")
        assert view.ingredients.snapshot() == before
        assert view.orders.gold == 0
        use(view, "plate")
    use(view, "box_sandwich")
    use(view, "plate")
    use(view, "plate")
    use(view, "serve")
    assert view.orders.gold == 100
    assert view.ingredients.snapshot().carrying_plate
    assert view.ingredients.snapshot().plate.ingredients == ()
    use(view, "serve")
    assert view.orders.gold == 100
    use(view, "plate")

    use(view, "serve")
    use(view, "box_noodles")
    use(view, "pot")
    use(view, "box_milk")
    use(view, "pot")
    assert view.pot.state == "cooking"
    press(view, arcade.key.P)
    view.on_update(5)
    assert view.pot.elapsed == 0
    press(view, arcade.key.P)
    view.on_update(4)
    assert view.pot.state == "ready"
    use(view, "pot")
    use(view, "plate")
    use(view, "plate")
    use(view, "serve")
    assert view.day_complete
    press(view, arcade.key.ENTER)
    assert view.ingredients.snapshot().carrying_plate
    assert "Return" in view.message
    use(view, "plate")
    assert not view.ingredients.snapshot().carrying_plate


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
        assert view.total_gold == 800
        view.on_draw()
        press(view, arcade.key.R)
        assert view.day_index == view.total_gold == 0
        assert not view.finished
    finally:
        window.close()


def test_expired_ticket_preserves_plate_and_repeats_recipe():
    window = create_window(visible=False)
    try:
        view = window.current_view
        use(view, "serve")
        use(view, "box_sandwich")
        use(view, "plate")
        old = view.orders.snapshot()
        view.on_update(61)
        assert view.orders.stats().expired == 1
        assert view.orders.snapshot().order_id != old.order_id
        assert view.orders.snapshot().required == old.required
        assert view.ingredients.snapshot().plate.ingredients == ("sandwich",)
    finally:
        window.close()
