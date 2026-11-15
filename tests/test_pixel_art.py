"""Check that art enlarges cleanly and texture uploads survive day resets."""
from math import ceil

import arcade
import pytest

from restaurant.display import artwork_viewport, fitted_window_size
from restaurant.game_view import create_window
from restaurant.pixel_art import ART_SIZE
from restaurant.shared.settings import WINDOW_HEIGHT, WINDOW_WIDTH


class FakeWindow:
    def __init__(self, framebuffer_size, pixel_ratio):
        self._framebuffer_size = framebuffer_size
        self._pixel_ratio = pixel_ratio

    def get_framebuffer_size(self):
        return self._framebuffer_size

    def get_pixel_ratio(self):
        return self._pixel_ratio


@pytest.mark.parametrize("dpi", [1.0, 1.25, 1.5, 2.0])
def test_fitted_window_can_draw_exactly_two_physical_pixels_per_art_pixel(dpi):
    width, height = fitted_window_size(1920, 1040, dpi)
    window = FakeWindow((int(width * dpi), int(height * dpi)), dpi)
    viewport = artwork_viewport(window)

    assert viewport.width * dpi == pytest.approx(2 * ART_SIZE[0])
    assert viewport.height * dpi == pytest.approx(2 * ART_SIZE[1])


def test_small_window_keeps_the_whole_scene_visible():
    width, height = 1000, 680
    viewport = artwork_viewport(FakeWindow((width, height), 1.25))
    assert width - 1 <= viewport.width * 1.25 <= width
    assert viewport.height * 1.25 < height
    assert viewport.width / viewport.height == pytest.approx(WINDOW_WIDTH / WINDOW_HEIGHT, abs=.005)


@pytest.fixture(scope="module")
def window():
    # Seeded orders: every restart shows the same first ticket and icons.
    game_window = create_window(visible=False, seed=1)
    yield game_window
    game_window.close()


def test_day_resets_do_not_upload_duplicate_worktop_images(window):
    view = window.current_view
    view.on_draw()
    textures = set(window.pixel_painter.textures)
    assert textures

    for _ in range(3):
        view.reset()
        view.on_draw()
        assert set(window.pixel_painter.textures) == textures
        assert window.ctx.active_framebuffer is window.ctx.screen


def test_present_restores_screen_and_repeats_each_art_pixel_twice(window):
    dpi = window.get_pixel_ratio()
    window.set_size(ceil(WINDOW_WIDTH / dpi), ceil(WINDOW_HEIGHT / dpi))
    viewport = artwork_viewport(window)
    canvas = window.current_view.art
    canvas.begin()
    assert window.ctx.active_framebuffer is canvas.framebuffer

    # Four source texels with different colors make filtering visible.
    colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255))
    for index, color in enumerate(colors):
        arcade.draw_lbwh_rectangle_filled(index % 2 * 2, index // 2 * 2, 2, 2, color)
    canvas.present()
    assert window.ctx.active_framebuffer is window.ctx.screen

    left, bottom = round(viewport.left * dpi), round(viewport.bottom * dpi)
    result = window.ctx.screen.read(viewport=(left, bottom, 4, 4), components=3)
    expected = bytes(channel for y in range(4) for x in range(4)
                     for channel in colors[y // 2 * 2 + x // 2])
    assert result == expected
