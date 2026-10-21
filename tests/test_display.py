"""Regression: DPI scaling must not make the whole window exceed the desktop."""
import pytest

from restaurant.display import fitted_window_size, scene_viewport, window_geometry
from restaurant.game_view import create_window
from restaurant.shared.settings import WINDOW_HEIGHT, WINDOW_WIDTH


@pytest.mark.parametrize("work_size", [(1920, 1040), (1366, 728), (1280, 680)])
@pytest.mark.parametrize("dpi", [1.0, 1.25, 1.5, 2.0])
def test_physical_window_fits_work_area_at_common_windows_scales(work_size, dpi):
    width, height = fitted_window_size(*work_size, dpi)
    assert width * dpi <= work_size[0] - 64
    assert height * dpi <= work_size[1] - 100
    assert width <= 1040
    assert abs(width / height - WINDOW_WIDTH / WINDOW_HEIGHT) < 0.01


@pytest.mark.parametrize("size", [(1280, 768), (800, 700), (1100, 500)])
def test_resize_keeps_complete_scene_without_stretching(size):
    viewport = scene_viewport(*size)
    assert viewport.width <= size[0] and viewport.height <= size[1]
    assert viewport.left >= 0 and viewport.bottom >= 0
    assert abs(viewport.width / viewport.height - WINDOW_WIDTH / WINDOW_HEIGHT) < 0.01


def test_real_fitted_window_and_resize_render_the_whole_room():
    window = create_window(visible=False)
    try:
        geometry = window_geometry(window)
        _, _, work_width, work_height = geometry["work_area_pixels"]
        pixel_width, pixel_height = geometry["framebuffer_pixels"]
        assert pixel_width <= work_width - 60
        assert pixel_height <= work_height - 96
        if "outer_rectangle_pixels" in geometry:
            left, top, right, bottom = geometry["outer_rectangle_pixels"]
            work_left, work_top, _, _ = geometry["work_area_pixels"]
            assert left >= work_left and top >= work_top
            assert right <= work_left + work_width and bottom <= work_top + work_height
        view = window.current_view
        for size in ((800, 600), (960, 480)):
            window.set_size(*size)
            view.on_draw()
            viewport = view.camera.viewport
            assert viewport.width <= window.width and viewport.height <= window.height
            assert abs(viewport.width / viewport.height - WINDOW_WIDTH / WINDOW_HEIGHT) < 0.01
            assert view.camera.projection.width == WINDOW_WIDTH
            assert view.camera.projection.height == WINDOW_HEIGHT
    finally:
        window.close()
