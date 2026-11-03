"""Real hidden-window checks for the independent ingredient demo."""
import arcade
import pytest

from demos.ingredients_demo import IngredientsDemo, TARGETS, create_window
from restaurant.ingredients.renderer import IngredientRenderer


@pytest.fixture(scope="module")
def window():
    window = create_window(visible=False)
    yield window
    window.close()


@pytest.fixture
def view(window):
    view = IngredientsDemo()
    window.show_view(view)
    return view


def press(view, key):
    view.on_key_press(key, 0)
    view.on_key_release(key, 0)


def test_controls_capacity_feedback_and_reset(view):
    for key in (arcade.key.KEY_1, arcade.key.KEY_2, arcade.key.KEY_3, arcade.key.KEY_4):
        press(view, key)
        press(view, arcade.key.A)
    assert view.system.snapshot().plate.ingredients == ("sandwich", "tomato", "noodles", "milk")
    press(view, arcade.key.KEY_2)
    press(view, arcade.key.A)
    assert not view.latest.success
    assert view.latest.message == "Plate is full"
    assert view.system.snapshot().held == "tomato"
    press(view, arcade.key.B)
    assert len(view.system.snapshot().plate.ingredients) == 4
    press(view, arcade.key.Q)
    assert view.system.snapshot().held == "milk"
    press(view, arcade.key.B)
    press(view, arcade.key.B)
    assert view.system.snapshot().plate.ingredients == ()
    press(view, arcade.key.R)
    assert view.system.snapshot().plate.revision == 0
    assert view.system.snapshot().held is None


def test_key_repeat_is_ignored_and_focus_loss_releases_keys(view, window):
    press(view, arcade.key.KEY_1)
    press(view, arcade.key.A)
    press(view, arcade.key.KEY_2)
    press(view, arcade.key.A)
    view.on_key_press(arcade.key.B, 0)
    assert view.latest.success
    view.on_key_press(arcade.key.B, 0)
    assert view.latest.success  # Repeating B did not attempt another discard.
    window.on_deactivate()
    assert not view.pressed
    press(view, arcade.key.B)
    assert not view.latest.success


def test_render_empty_full_and_held_snapshots_without_mutating_state(view):
    assert set(view.renderer._textures) == {
        "sandwich", "tomato", "noodles", "milk", "plate",
        "box_sandwich", "box_tomato", "box_noodles", "box_milk",
    }
    view.on_draw()
    for key in (arcade.key.KEY_1, arcade.key.KEY_2, arcade.key.KEY_3, arcade.key.KEY_4):
        press(view, key)
        view.on_draw()
        press(view, arcade.key.A)
    before = view.system.snapshot()
    view.on_draw()
    view.on_draw()
    assert view.system.snapshot() == before
    assert arcade.get_image().getbbox() is not None


def test_renderer_works_without_artwork(view, monkeypatch, tmp_path):
    monkeypatch.setattr("restaurant.ingredients.renderer.ASSET_DIRECTORY", tmp_path)
    renderer = IngredientRenderer()
    assert renderer._textures == {}
    press(view, arcade.key.KEY_2)
    before = view.system.snapshot()
    renderer.draw(before, (130, 185), TARGETS)
    assert view.system.snapshot() == before
