"""Check the hand animation through normal kitchen controls."""
import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.kitchen.layout import ANIMATION_TEST_POSITION
from restaurant.player.controller import PICKUP_SECONDS
from restaurant.shared.contracts import PlateLocation


@pytest.fixture
def view():
    window = create_window(visible=False)
    try:
        yield window.current_view
    finally:
        window.close()


def use_station(view, target_id):
    target = next(target for target in view.targets if target.target_id == target_id)
    view.player.sprite.position = target.x, target.y
    view.on_key_press(arcade.key.E, 0)
    view.on_update(0)
    view.on_key_release(arcade.key.E, 0)


def hand_offset(player):
    return tuple(anchor - foot for anchor, foot in zip(player.hand_anchor, player.ground_position))


def test_pickup_lifts_once_and_discard_clears_the_drawn_item(view, monkeypatch):
    player = view.player
    use_station(view, "box_tomato")
    assert view.ingredients.snapshot().held == "tomato"
    start_y = player.hand_anchor[1]
    start_size = player.hand_item_size
    view.on_update(PICKUP_SECONDS / 2)
    middle_y = player.hand_anchor[1]
    middle_size = player.hand_item_size
    view.on_update(PICKUP_SECONDS / 2)
    settled = player.hand_anchor
    settled_size = player.hand_item_size
    assert start_y < middle_y < settled[1]
    assert start_size < middle_size < settled_size
    view.on_update(PICKUP_SECONDS)
    assert (player.hand_anchor, player.hand_item_size) == (settled, settled_size)

    drawn = []
    draw_food = view.kitchen.draw_food

    def record_food(ingredient, x, y, size):
        drawn.append(ingredient)
        draw_food(ingredient, x, y, size)

    monkeypatch.setattr(view.kitchen, "draw_food", record_food)
    view.on_draw()
    assert drawn == ["tomato"]
    use_station(view, "bin")
    assert view.ingredients.snapshot().held is None
    drawn.clear()
    view.on_draw()
    assert drawn == []
    use_station(view, "box_tomato")
    assert player.hand_item_size == pytest.approx(start_size)


@pytest.mark.parametrize("key,direction", [
    (arcade.key.W, "up"), (arcade.key.A, "left"),
    (arcade.key.S, "down"), (arcade.key.D, "right"),
])
def test_releasing_movement_restores_the_directional_standing_grip(view, key, direction):
    player = view.player
    use_station(view, "box_sandwich")
    view.on_update(PICKUP_SECONDS)
    player.sprite.position = ANIMATION_TEST_POSITION

    view.on_key_press(key, 0)
    view.on_update(0.05)
    walking_grip = hand_offset(player)
    walking_texture = player.sprite.texture
    view.on_key_release(key, 0)
    standing_grip = hand_offset(player)
    standing_texture = player.sprite.texture
    assert player.direction == direction
    assert player.state == "idle"
    assert standing_texture is not walking_texture
    assert standing_grip != pytest.approx(walking_grip)

    view.on_key_press(key, 0)
    view.on_update(0.05)
    view.on_key_release(key, 0)
    view.on_update(0.2)
    assert player.sprite.texture is standing_texture
    assert hand_offset(player) == pytest.approx(standing_grip)
    assert view.ingredients.snapshot().held == "sandwich"


def test_chopping_and_carrying_plate_do_not_show_a_loose_item_grip(view):
    use_station(view, "box_tomato")
    assert view.player.hand_anchor is not None
    use_station(view, "chopping_board")
    assert view.player.state == "chop"
    assert view.ingredients.snapshot().held is None
    assert view.player.hand_anchor is None
    view.on_draw()

    view.reset()
    use_station(view, "plate")
    use_station(view, "box_tomato")
    state = view.ingredients.snapshot()
    assert state.plate.location is PlateLocation.CARRIED
    assert state.plate.ingredients == ("tomato",)
    assert state.held is None
    assert view.player.hand_anchor is None
    assert view.player.plate_anchor is not None
    view.on_draw()
