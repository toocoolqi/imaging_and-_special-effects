"""Real hidden OpenGL window: input routing, pause, focus, hooks and rendering.

Requires a graphics-capable desktop, just like the demo. Failures are not skipped.
"""
import arcade
import pytest

from restaurant.game_view import create_window


@pytest.fixture(scope="module")
def window():
    window = create_window(visible=False)
    yield window
    window.close()


@pytest.fixture
def view(window):
    view = window.current_view
    view.reset()
    return view


def test_shared_direction_keys(view):
    view.on_key_press(arcade.key.W, 0)
    view.on_key_press(arcade.key.UP, 0)
    view.on_key_release(arcade.key.W, 0)
    before = view.player.position
    view.on_update(0.1)
    assert view.player.position[1] > before[1]
    view.on_key_release(arcade.key.UP, 0)
    before = view.player.position
    view.on_update(0.1)
    assert view.player.position == before


def test_one_action_per_press_and_plate_hook(view):
    view.player.reset((450, 275))
    for _ in range(5):
        view.on_key_press(arcade.key.E, 0)
    view.on_update(1 / 60)
    assert view.interaction_count == 1
    assert "plate" in view.message
    view.on_update(1 / 60)
    assert view.interaction_count == 1
    view.on_key_release(arcade.key.E, 0)
    view.on_key_press(arcade.key.E, 0)
    view.on_key_press(arcade.key.Q, 0)
    view.on_update(1 / 60)
    assert view.interaction_count == 3
    assert "REMOVE" in view.message


def test_pause_reset_and_focus_loss(view, window):
    view.on_key_press(arcade.key.W, 0)
    view.on_key_press(arcade.key.E, 0)
    view.on_key_press(arcade.key.P, 0)
    before = view.player.position
    view.on_update(1)
    assert view.player.position == before
    assert not view.actions
    view.on_key_release(arcade.key.P, 0)
    view.on_key_press(arcade.key.P, 0)
    view.on_update(0.1)
    assert view.player.position == before
    view.on_key_press(arcade.key.W, 0)
    window.on_deactivate()
    view.on_update(0.1)
    assert view.player.position == before
    view.on_key_press(arcade.key.R, 0)
    assert not view.paused
    assert view.interaction_count == 0


def test_out_of_range_and_wrong_q_target(view):
    view.on_key_press(arcade.key.E, 0)
    view.on_update(0.01)
    assert view.interaction_count == 0
    view.player.reset((130, 520))
    view.on_key_press(arcade.key.Q, 0)
    view.on_update(0.01)
    assert view.interaction_count == 0
    assert "plate" in view.message


def test_real_render_all_directions_debug_and_pause(view):
    for key in (arcade.key.W, arcade.key.S, arcade.key.A, arcade.key.D):
        view.player.reset((250, 300))
        view.on_key_press(key, 0)
        for _ in range(4):
            view.on_update(0.14)
            view.on_draw()
        view.on_key_release(key, 0)
    view.on_key_press(arcade.key.F1, 0)
    view.on_draw()
    view.on_key_press(arcade.key.P, 0)
    view.on_draw()
    assert arcade.get_image().getbbox() is not None
