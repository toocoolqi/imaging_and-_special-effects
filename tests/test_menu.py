"""Menu interactions use the displayed UI coordinates after window resizing."""
import arcade

from restaurant.menu import MainMenu, PLAY_BUTTON
from restaurant.shared.settings import WINDOW_HEIGHT, WINDOW_WIDTH


def test_play_click_after_letterbox_resize():
    window = arcade.Window(1040, 600, visible=False, antialiasing=False, resizable=True)
    try:
        game = arcade.View()
        menu = MainMenu(lambda: window.show_view(game))
        window.show_view(menu)
        window.set_size(800, 650)
        menu.on_draw()

        # The apparent centre uses the same framebuffer letterbox as the art.
        menu.on_mouse_press(24, 24, arcade.MOUSE_BUTTON_LEFT, 0)
        assert window.current_view is menu
        viewport = menu.display_viewport()
        x = round(viewport.left + viewport.width * PLAY_BUTTON.center_x / WINDOW_WIDTH)
        y = round(viewport.bottom + viewport.height * PLAY_BUTTON.center_y / WINDOW_HEIGHT)
        menu.on_mouse_press(x, y, arcade.MOUSE_BUTTON_RIGHT, 0)
        assert window.current_view is menu
        menu.on_mouse_press(x, y, arcade.MOUSE_BUTTON_LEFT, 0)
        assert window.current_view is game
    finally:
        window.close()


def test_enter_starts_the_game_only_once():
    window = arcade.Window(800, 600, visible=False, antialiasing=False)
    try:
        calls = []
        menu = MainMenu(lambda: calls.append("start"))
        window.show_view(menu)
        menu.on_key_press(arcade.key.SPACE, 0)
        menu.on_key_press(arcade.key.ENTER, 0)
        menu.on_key_press(arcade.key.ENTER, 0)
        assert calls == ["start"]
    finally:
        window.close()
