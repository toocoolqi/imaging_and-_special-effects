"""Task 2 works through real kitchen inputs, not just its independent lab."""
import arcade

from restaurant.game_view import create_window
from restaurant.shared.contracts import PlateLocation
from restaurant.shared.settings import TARGETS


def use(view, target_id, key=arcade.key.E):
    target = next(t for t in TARGETS if t.target_id == target_id)
    view.player.reset((target.x, target.y))
    view.on_key_press(key, 0)
    view.on_update(1 / 60)
    view.on_key_release(key, 0)


def test_pickup_plate_remove_discard_and_reset_in_kitchen():
    window = create_window(visible=False)
    try:
        view = window.current_view
        use(view, "box_tomato")
        assert view.ingredients.snapshot().held == "tomato"
        use(view, "box_milk")  # Full hands do not overwrite the tomato.
        assert view.ingredients.snapshot().held == "tomato"
        use(view, "plate")
        assert view.ingredients.snapshot().plate.ingredients == ("tomato",)
        use(view, "box_noodles")
        use(view, "plate")
        view.on_draw()  # Both task 2 icons appear on the real plate.
        use(view, "plate", arcade.key.Q)
        assert view.ingredients.snapshot().held == "noodles"
        use(view, "bin")
        assert view.ingredients.snapshot().held is None
        assert view.ingredients.snapshot().plate.ingredients == ("tomato",)
        use(view, "bin")
        assert not view.ingredients.snapshot().plate.ingredients
        use(view, "box_sandwich")
        view.reset()
        assert view.ingredients.snapshot().held is None
        assert view.ingredients.snapshot().plate.revision == 0
    finally:
        window.close()


def test_paused_food_actions_do_not_mutate_state():
    window = create_window(visible=False)
    try:
        view = window.current_view
        view.on_key_press(arcade.key.P, 0)
        before = view.ingredients.snapshot()
        use(view, "box_milk")
        assert view.ingredients.snapshot() == before
    finally:
        window.close()


def test_pick_up_empty_plate_and_collect_food_directly():
    window = create_window(visible=False)
    try:
        view = window.current_view
        use(view, "plate")
        assert view.ingredients.snapshot().plate.location is PlateLocation.CARRIED
        use(view, "box_tomato")
        use(view, "box_sandwich")
        assert view.ingredients.snapshot().held is None
        assert view.ingredients.snapshot().plate.ingredients == ("tomato", "sandwich")
        use(view, "plate")
        assert view.ingredients.snapshot().plate.location is PlateLocation.DOCKED
        assert view.ingredients.snapshot().plate.ingredients == ("tomato", "sandwich")
    finally:
        window.close()
