"""Mouse and keyboard entry point before the first restaurant day."""
from collections.abc import Callable

import arcade

from restaurant.display import artwork_viewport
from restaurant.kitchen.details import PixelDetails
from restaurant.kitchen.scene import load_textures
from restaurant.pixel_art import PixelCanvas, draw_pixel_texture
from restaurant.player.controller import ASSET_DIR as CHEF_DIR
from restaurant.shared.settings import WINDOW_HEIGHT, WINDOW_WIDTH


INK = (29, 44, 41)
PAPER = (249, 229, 185)
MUTED = (90, 98, 74)
GOLD = (196, 137, 72)
TEAL = (51, 100, 83)
TEAL_LIGHT = (67, 123, 100)
PLAY_BUTTON = arcade.LBWH(112, 218, 366, 64)
QUIT_BUTTON = arcade.LBWH(112, 148, 366, 50)

# The title is drawn from square pixels so its edges match the game artwork.
TITLE_PIXELS = {
    "A": ("01110", "11011", "11011", "11111", "11011", "11011", "11011"),
    "C": ("01111", "11000", "11000", "11000", "11000", "11000", "01111"),
    "E": ("11111", "11000", "11000", "11110", "11000", "11000", "11111"),
    "F": ("11111", "11000", "11000", "11110", "11000", "11000", "11000"),
    "H": ("11011", "11011", "11011", "11111", "11011", "11011", "11011"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("11000", "11000", "11000", "11000", "11000", "11000", "11111"),
    "S": ("01111", "11000", "11000", "01110", "00011", "00011", "11110"),
}


def draw_title(art, title, left, top, unit):
    pixels = [(left + (letter_index * 6 + col) * unit, top - (row + 1) * unit)
              for letter_index, letter in enumerate(title)
              for row, line in enumerate(TITLE_PIXELS[letter])
              for col, value in enumerate(line) if value == "1"]
    for x, y in pixels:
        art.rect(x + 3, y - 3, unit, unit, (208, 174, 122))
    for x, y in pixels:
        art.rect(x, y, unit, unit, INK)


def menu_art():
    art = PixelDetails()
    rect = art.rect
    frame = art.frame
    rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, (26, 40, 35))
    frame(50, 52, WINDOW_WIDTH - 100, WINDOW_HEIGHT - 104, (114, 76, 54),
          edge=(17, 29, 25), thickness=4)
    rect(58, 637, WINDOW_WIDTH - 116, 7, GOLD)
    rect(58, 60, WINDOW_WIDTH - 116, 7, (68, 46, 35))
    frame(76, 82, 462, 540, PAPER, edge=(65, 49, 38), thickness=4)
    rect(80, 614, 454, 4, (255, 243, 209))
    rect(80, 86, 454, 8, (222, 192, 142))
    draw_title(art, "CLASSIC", 112, 562, 9)
    draw_title(art, "CHEF", 112, 489, 12)
    rect(112, 373, 366, 3, (217, 179, 124))

    # A kitchen vignette made from the same tiles, cabinet art, and warm trim.
    frame(552, 82, 588, 540, (183, 151, 112), edge=(62, 47, 35), thickness=4)
    rect(564, 302, 564, 308, (228, 205, 158))
    for y in range(330, 592, 34):
        rect(564, y, 564, 2, (203, 176, 129))
        for x in range(564 + 36 * (y % 4 == 0), 1128, 72):
            rect(x, y, 2, min(34, 610 - y), (203, 176, 129))
    rect(564, 305, 564, 8, (48, 87, 70))
    rect(564, 313, 564, 9, (108, 144, 111))
    for row, y in enumerate(range(96, 305, 38)):
        for col, x in enumerate(range(564, 1128, 38)):
            width, height = min(36, 1128 - x), min(36, 305 - y)
            tone = (218, 188, 139) if (row + col) % 2 == 0 else (233, 204, 158)
            rect(x, y, width, height, tone)
            if row % 2 == 0 and col % 3 == 1:
                rect(x + 15, y + 8, 5, 20, (151, 150, 104))
                rect(x + 8, y + 15, 19, 5, (151, 150, 104))
    rect(564, 96, 564, 8, (146, 96, 63))
    rect(564, 602, 564, 8, (242, 218, 176))
    return art


class MainMenu(arcade.View):
    def __init__(self, start_game: Callable[[], None]):
        super().__init__()
        self.start_game = start_game
        self.started = False
        self.pointer = (-1, -1)
        self.canvas = PixelCanvas(self.window)
        self.ui_camera = arcade.Camera2D(position=(0, 0))
        self.art = menu_art()
        self.textures = load_textures()
        self.chef = arcade.load_texture(CHEF_DIR / "down_4.png")
        self.labels = {}
        self.view_size = None

    def display_viewport(self):
        """Use the logical viewport Arcade scales to the physical screen."""
        return artwork_viewport(self.window)

    def button_at(self, x, y):
        viewport = self.display_viewport()
        world_x = (x - viewport.left) * WINDOW_WIDTH / viewport.width
        world_y = (y - viewport.bottom) * WINDOW_HEIGHT / viewport.height
        for button, name in ((PLAY_BUTTON, "play"), (QUIT_BUTTON, "quit")):
            if button.left <= world_x < button.right and button.bottom <= world_y < button.top:
                return name
        return None

    def on_mouse_motion(self, x, y, dx, dy):
        self.pointer = (x, y)

    def on_mouse_leave(self, x, y):
        self.pointer = (-1, -1)

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        action = self.button_at(x, y)
        if action == "play":
            self.play()
        elif action == "quit":
            self.window.close()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ENTER:
            self.play()
        elif symbol == arcade.key.ESCAPE:
            self.window.close()

    def play(self):
        if not self.started:
            self.started = True
            self.start_game()

    def draw_picture(self, key, x, y, width, height):
        texture = self.chef if key == "chef" else self.textures[key]
        draw_pixel_texture(texture, arcade.XYWH(x, y, width, height))

    def draw_kitchen(self):
        self.draw_picture("spice_shelf", 715, 531, 202, 98)
        self.draw_picture("service_hatch", 972, 510, 258, 131)
        self.draw_picture("sink", 695, 384, 222, 104)
        self.draw_picture("stove", 1035, 364, 141, 142)
        self.draw_picture("pot", 1006, 414, 46, 37)
        self.draw_picture("crate_tomato", 656, 225, 79, 108)
        self.draw_picture("crate_sandwich", 1070, 203, 75, 103)
        for x, y, w, h in ((795, 151, 104, 18), (786, 154, 122, 12)):
            arcade.draw_lbwh_rectangle_filled(x, y, w, h, (129, 108, 78))
        self.draw_picture("chef", 849, 328, self.chef.width * 4, self.chef.height * 4)

    def label(self, value, x, y, size, color=INK, *, bold=False, center=False):
        if value not in self.labels:
            viewport = self.display_viewport()
            scale = viewport.width / WINDOW_WIDTH
            ratio = self.window.get_pixel_ratio()
            self.labels[value] = arcade.Text(
                value, (viewport.left + x * scale) * ratio,
                (viewport.bottom + y * viewport.height / WINDOW_HEIGHT) * ratio,
                color, size * scale * ratio, bold=bold, anchor_y="center",
                anchor_x="center" if center else "left",
            )
        self.labels[value].draw()

    def on_draw(self):
        self.canvas.begin()
        self.art.draw()
        self.draw_kitchen()
        hovered = self.button_at(*self.pointer)
        for button, name in ((PLAY_BUTTON, "play"), (QUIT_BUTTON, "quit")):
            color = ((TEAL_LIGHT if hovered == name else TEAL) if name == "play"
                     else ((232, 203, 151) if hovered == name else (242, 219, 174)))
            x, y, width, height = button.lbwh
            arcade.draw_lbwh_rectangle_filled(x + 3, y - 4, width, height, (173, 135, 92))
            arcade.draw_lbwh_rectangle_filled(x, y, width, height, INK)
            arcade.draw_lbwh_rectangle_filled(x + 3, y + 3, width - 6, height - 6, color)
        self.canvas.present()
        size = self.window.width, self.window.height, self.window.scale
        if size != self.view_size:
            self.labels.clear()
            self.view_size = size
        self.ui_camera.viewport = arcade.LBWH(0, 0, self.window.width, self.window.height)
        ratio = self.window.get_pixel_ratio()
        self.ui_camera.projection = arcade.LRBT(
            0, self.window.width * ratio, 0, self.window.height * ratio)
        self.ui_camera.use()
        self.label("Cook and serve across four kitchens.", 112, 340, 16)
        self.label("Play", PLAY_BUTTON.center_x, PLAY_BUTTON.center_y, 22,
                   (255, 245, 220), bold=True, center=True)
        self.label("Quit", QUIT_BUTTON.center_x, QUIT_BUTTON.center_y, 16,
                   bold=True, center=True)
        self.label("Enter  Play     Esc  Quit", 112, 113, 12, MUTED)
