"""Static portraits on the shared art grid, with code-driven motion and effects."""
from math import cos, sin, pi
from pathlib import Path

import arcade

from restaurant.pixel_art import draw_pixel_texture

ROOT = Path(__file__).resolve().parents[2] / "assets" / "enemies"
GHOST = (197, 198, 243)
RED = (213, 91, 113)
GOLD = (250, 204, 78)


class EncounterArt:
    def __init__(self):
        self.textures = {}
        for name in ("ghost", "blocker", "vampire"):
            texture = arcade.load_texture(ROOT / f"{name}.png")
            # Only remove transparent padding at load time. Original generated
            # PNGs are retained; the shared pixel canvas handles sharp scaling.
            # Match the renderer's alpha cutoff when measuring the silhouette;
            # nearly invisible generator noise must not shrink the character.
            bounds = texture.image.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
            if bounds:
                left, top, right, bottom = bounds
                texture = texture.crop(left, top, right - left, bottom - top)
            self.textures[name] = texture

    def sprite(self, name, x, foot_y, width, height, direction=-1):
        draw_pixel_texture(self.textures[name], arcade.XYWH(
            x, foot_y + height / 2, -width if direction == 1 else width, height))

    def floor(self, encounters, text):
        t = encounters.elapsed
        b = encounters.blocker
        if b:
            if b.state == "warning":
                alpha = int(95 + 60 * sin(t * 10))
                arcade.draw_ellipse_filled(b.x, b.y, 100, 44, (*GOLD, alpha))
                arcade.draw_ellipse_outline(b.x, b.y, 100, 44, GOLD, 2)
                text("blocker_warning", "GUEST STOPPING HERE", b.x, b.y - 35, 10,
                     GOLD, anchor_x="center", bold=True)
            else:
                arcade.draw_ellipse_filled(b.x, b.y - 5, 92, 22, (39, 28, 33, 110))
        v = encounters.vampire
        if v:
            warning = v.state == "warning"
            alpha = int(42 + 20 * sin(t * 12)) if warning else 22
            arcade.draw_lbwh_rectangle_filled(20, v.y - 27, 920, 54, (*RED, alpha))
            for side in (-1, 1):
                arcade.draw_line(20, v.y + side * 27, 940, v.y + side * 27, (*RED, 180), 2)
            if warning:
                # Repeated directional chevrons explain where the sweep goes.
                for x in range(80, 920, 100):
                    tip = x + v.direction * 12
                    arcade.draw_line(x, v.y - 9, tip, v.y, RED, 3)
                    arcade.draw_line(tip, v.y, x, v.y + 9, RED, 3)
                arcade.draw_lbwh_rectangle_filled(310, v.y - 55, 340, 23, (61, 34, 48, 230))
                text("vampire_warning", "VAMPIRE  /  LEAVE THE RED LANE", 480, v.y - 48,
                     12, (255, 229, 211), anchor_x="center", bold=True)
        g = encounters.ghost
        if g and g.state == "warning":
            x, y = encounters.plate
            arcade.draw_ellipse_outline(x, y + 20, 94, 30, GHOST, 3)

    def blocker(self, encounters):
        b = encounters.blocker
        if b and b.state == "blocking":
            self.sprite("blocker", b.x, b.y - 6, 140, 184)
            # A little impatience cloud, not another animation frame.
            x, y = b.x + 55, b.y + 150
            arcade.draw_lbwh_rectangle_filled(x - 8, y - 2, 16, 20, (248, 231, 190))
            arcade.draw_lbwh_rectangle_filled(x - 1, y + 5, 3, 9, (99, 57, 45))
            arcade.draw_lbwh_rectangle_filled(x - 1, y, 3, 3, (99, 57, 45))

    def air(self, encounters, player, kitchen, text):
        t = encounters.elapsed
        g = encounters.ghost
        if g and g.state != "warning":
            bob = sin(t * 4.5) * 6
            arcade.draw_ellipse_filled(g.x, g.y - 3, 58, 14, (58, 54, 83, 55))
            for i in range(3):
                x = g.x + sin(t * 2 + i * 2) * 52
                y = g.y + 35 + i * 28
                arcade.draw_lbwh_rectangle_filled(x, y, 4, 4, (*GHOST, 170))
            self.sprite("ghost", g.x, g.y + 24 + bob, 118, 118)
            if g.food:
                kitchen.draw_plate_food(g.food, g.x, g.y + 72 + bob, 19)
            if encounters.ghost_in_reach(player.ground_position):
                arcade.draw_lbwh_rectangle_filled(g.x - 55, g.y + 154 + bob, 110, 23, (44, 39, 69, 235))
                text("ghost_e", "E  RECLAIM" if g.food else "E  BANISH", g.x, g.y + 160 + bob,
                     12, (244, 237, 255), anchor_x="center", bold=True)
        v = encounters.vampire
        if v and v.state == "sweep":
            for i in range(1, 5):
                x = v.x - v.direction * (50 + i * 17)
                arcade.draw_line(x, v.y + 45 + (i % 2) * 12, x - v.direction * 24,
                                 v.y + 45 + (i % 2) * 12, (*RED, 180 - i * 28), 4)
            self.sprite("vampire", v.x, v.y + 12, 160, 138, v.direction)
        px, py = player.ground_position
        if encounters.stun:
            for i in range(3):
                angle = t * 7 + i * 2 * pi / 3
                x, y = px + cos(angle) * 34, py + 194 + sin(angle) * 10
                arcade.draw_lbwh_rectangle_filled(x - 5, y - 2, 10, 4, GOLD)
                arcade.draw_lbwh_rectangle_filled(x - 2, y - 5, 4, 10, GOLD)
            text("stun_label", "STUNNED", px, py - 28, 11, GOLD, anchor_x="center", bold=True)
        if encounters.flash:
            arcade.draw_circle_outline(px, py + 80, 42 + 60 * (0.22 - encounters.flash), (*RED, 230), 4)
        if encounters.burst:
            x, y, kind, left = encounters.burst
            progress = max(0.0, 1 - left / 0.6)
            color = GHOST if kind == "ghost" else RED if kind == "bite" else (198, 160, 111)
            for i in range(8):
                angle = i * pi / 4
                radius = 12 + progress * 46
                arcade.draw_lbwh_rectangle_filled(x + cos(angle) * radius,
                    y + sin(angle) * radius, 6, 6, (*color, int(230 * (1 - progress))))
