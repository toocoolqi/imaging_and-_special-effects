"""Fit the app inside the desktop work area, including Windows DPI scaling.

Arcade uses logical window units; Windows may turn each into 1.25/1.5/2 physical
pixels. Desktop work-area dimensions are physical pixels. Never compare those
two sizes without applying the window's DPI scale.
"""
import sys

import arcade

from restaurant.shared.settings import WINDOW_HEIGHT, WINDOW_WIDTH


def work_area(window):
    """Return (left, top, width, height); exclude the Windows taskbar."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                        ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        # Arcade's pinned Windows backend provides the handle of OUR window.
        handle = getattr(window, "_hwnd", None)
        monitor = user32.MonitorFromWindow(handle, 1)
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            rect = info.work
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    return 0, 0, *arcade.get_display_size()


def fitted_window_size(width, height, dpi_scale=1.0):
    """Prefer 1040 logical pixels wide, retaining aspect ratio and frame margins."""
    scale = min(1040 / WINDOW_WIDTH,
                max(1, width - 64) / (WINDOW_WIDTH * dpi_scale),
                max(1, height - 100) / (WINDOW_HEIGHT * dpi_scale))
    return max(1, int(WINDOW_WIDTH * scale)), max(1, int(WINDOW_HEIGHT * scale))


def scene_viewport(width, height):
    """Fit the complete scene without stretching it when the user resizes."""
    scale = min(width / WINDOW_WIDTH, height / WINDOW_HEIGHT)
    scene_width = max(1, int(WINDOW_WIDTH * scale))
    scene_height = max(1, int(WINDOW_HEIGHT * scale))
    return arcade.LBWH((width - scene_width) // 2, (height - scene_height) // 2,
                       scene_width, scene_height)


def fit_window(window):
    left, top, width, height = work_area(window)
    window.set_size(*fitted_window_size(width, height, window.scale))
    pixels_w, pixels_h = window.get_framebuffer_size()
    window.set_location(left + (width - pixels_w) // 2,
                        top + (height - pixels_h) // 2)


def window_geometry(window):
    """Small diagnostic used by the packaged check; no personal desktop capture."""
    geometry = {"logical_size": window.get_size(),
            "framebuffer_pixels": window.get_framebuffer_size(),
            "dpi_scale": window.scale, "work_area_pixels": work_area(window),
            "client_location_pixels": window.get_location()}
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL
        rect = wintypes.RECT()
        if user32.GetWindowRect(getattr(window, "_hwnd", None), ctypes.byref(rect)):
            geometry["outer_rectangle_pixels"] = (rect.left, rect.top, rect.right, rect.bottom)
    return geometry
