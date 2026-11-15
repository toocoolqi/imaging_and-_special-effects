"""Living atmosphere for each kitchen condition (Arcade drawing only).

clean      warm: dust motes drifting in the light.  metal: glints on steel.
overgrown  water drips from the ceiling into the painted puddles, with
           ripple rings and a splash; fireflies wander above the plants.
damaged    broken wall panels throw electrical sparks; the lights flicker.

Nothing here is solid or changes gameplay: it is driven by delta time, so
pausing the game freezes it, and it uses the map's effect_points, the same
points the artwork painted puddles and broken panels at.
"""
from math import cos, pi, sin
import random

import arcade

from restaurant.kitchen.layout import FLOOR_TOP, KITCHEN_HEIGHT, KITCHEN_WIDTH


class _Mote:
    def __init__(self, rng, width, height, floor_top):
        self.x, self.y = rng.uniform(30, width - 30), rng.uniform(40, floor_top)
        self.phase, self.speed = rng.uniform(0, 2 * pi), rng.uniform(0.3, 0.9)
        self.drift = rng.uniform(4, 12)
        self.size = rng.uniform(1.0, 2.2)


class _Drip:
    FALL_HEIGHT = 230.0

    def __init__(self, x, y, delay):
        self.x, self.ground = x, y
        self.wait = delay          # seconds until the next drop forms
        self.height = None         # None = no drop falling
        self.speed = 0.0
        self.ripple = None         # age of the ripple, or None


class _Spark:
    def __init__(self, x, y, rng):
        angle = rng.uniform(-0.2 * pi, 1.2 * pi)
        speed = rng.uniform(80, 260)
        self.x, self.y = x, y
        self.vx, self.vy = cos(angle) * speed, sin(angle) * speed
        self.age, self.lifetime = 0.0, rng.uniform(0.25, 0.6)


class KitchenAmbience:
    """day is a restaurant.kitchen.days.KitchenDay."""

    def __init__(self, definition, play_sound=None, seed=None):
        self.definition = definition
        self.condition = definition.condition
        self.style = "metal" if definition.style.startswith("metal") else "warm"
        self.width, self.height, self.floor_top = KITCHEN_WIDTH, KITCHEN_HEIGHT, FLOOR_TOP
        self.rng = random.Random(seed)
        self.play_sound = play_sound or (lambda name: None)
        self.elapsed = 0.0
        self.motes = [_Mote(self.rng, self.width, self.height, self.floor_top)
                      for _ in range(16 if self.condition != "damaged" else 0)]
        self.drips, self.sparks, self.splashes = [], [], []
        self.spark_wait = [self.rng.uniform(1.0, 3.0) for _ in definition.effect_points]
        self.spark_flash = [0.0 for _ in definition.effect_points]
        self.flicker_wait = self.rng.uniform(3.0, 6.0)
        self.flicker = 0.0
        self.glints = []
        self.glint_wait = 0.6
        if self.condition == "overgrown":
            self.drips = [_Drip(x, y, self.rng.uniform(0.3, 2.5)) for x, y in definition.effect_points]
        self.glow = arcade.make_soft_circle_texture(128, (255, 236, 170), center_alpha=200, outer_alpha=0)
        # Steel worktops where a clean metal kitchen can catch the light.
        self.surfaces = [(p.x, p.y + p.height * 0.18, p.width * 0.8, p.height * 0.3)
                         for p in definition.props
                         if p.solid and p.asset in ("table", "sink", "pass_counter", "stove")]

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.elapsed += dt
        if self.condition == "overgrown":
            self._update_drips(dt)
        elif self.condition == "damaged":
            self._update_sparks(dt)
        elif self.style == "metal":
            self._update_glints(dt)

    def _update_drips(self, dt):
        for drip in self.drips:
            if drip.ripple is not None:
                drip.ripple += dt
                if drip.ripple > 0.9:
                    drip.ripple = None
            if drip.height is None:
                drip.wait -= dt
                if drip.wait <= 0:
                    drip.height, drip.speed = _Drip.FALL_HEIGHT, 0.0
            else:
                drip.speed += 900 * dt            # gravity
                drip.height -= drip.speed * dt
                if drip.height <= 0:              # hits the puddle
                    drip.height, drip.ripple = None, 0.0
                    drip.wait = self.rng.uniform(1.6, 4.5)
                    self.play_sound("drip")
                    for _ in range(5):
                        self.splashes.append([drip.x, drip.ground, self.rng.uniform(-50, 50),
                                              self.rng.uniform(50, 120), 0.0])
        for splash in self.splashes:
            splash[4] += dt
            splash[3] -= 420 * dt
            splash[0] += splash[2] * dt
            splash[1] += splash[3] * dt
        self.splashes = [s for s in self.splashes if s[4] < 0.35]

    def _update_sparks(self, dt):
        for index, (x, y) in enumerate(self.definition.effect_points):
            self.spark_flash[index] = max(0.0, self.spark_flash[index] - dt)
            self.spark_wait[index] -= dt
            if self.spark_wait[index] <= 0:
                self.spark_wait[index] = self.rng.uniform(2.2, 6.0)
                self.spark_flash[index] = 0.16
                self.sparks.extend(_Spark(x, y - 6, self.rng) for _ in range(self.rng.randint(9, 15)))
                self.play_sound("spark")
        for spark in self.sparks:
            spark.age += dt
            spark.vy -= 520 * dt
            spark.x += spark.vx * dt
            spark.y += spark.vy * dt
        self.sparks = [s for s in self.sparks if s.age < s.lifetime]
        # Failing fluorescent tubes: a short double dip in brightness.
        self.flicker = max(0.0, self.flicker - dt)
        self.flicker_wait -= dt
        if self.flicker_wait <= 0:
            self.flicker_wait = self.rng.uniform(3.5, 8.0)
            self.flicker = self.rng.uniform(0.25, 0.5)

    def _update_glints(self, dt):
        self.glint_wait -= dt
        if self.glint_wait <= 0 and self.surfaces:
            self.glint_wait = self.rng.uniform(0.5, 1.4)
            cx, cy, w, h = self.rng.choice(self.surfaces)
            self.glints.append([cx + self.rng.uniform(-w / 2, w / 2), cy + self.rng.uniform(-h / 2, h / 2), 0.0])
        for glint in self.glints:
            glint[2] += dt
        self.glints = [g for g in self.glints if g[2] < 0.7]

    # ------------------------------------------------------------ draw
    def draw_floor_layer(self):
        """Under the furniture and chef: ripples spreading on the puddles."""
        for drip in self.drips:
            if drip.ripple is not None:
                t = drip.ripple / 0.9
                for ring in (t, max(0.0, t - 0.3)):
                    if ring > 0:
                        alpha = int(190 * (1 - ring))
                        arcade.draw_ellipse_outline(drip.x, drip.ground, 8 + 30 * ring, 3 + 11 * ring,
                                                    (224, 240, 238, alpha), 1.5)

    def draw_air_layer(self):
        """Over the furniture: drops, sparks, motes, glints and light changes."""
        if self.condition == "overgrown":
            for drip in self.drips:
                if drip.height is not None:
                    y = drip.ground + drip.height
                    arcade.draw_line(drip.x, y + 9, drip.x, y, (190, 220, 226, 150), 2)
                    arcade.draw_circle_filled(drip.x, y, 2.5, (214, 236, 240, 230))
            for x, y, _, _, age in self.splashes:
                arcade.draw_circle_filled(x, y, 1.6, (224, 240, 238, int(230 * (1 - age / 0.35))))
            for mote in self.motes:               # fireflies: green-gold, twinkling
                x = mote.x + sin(self.elapsed * mote.speed + mote.phase) * mote.drift * 3
                y = mote.y + cos(self.elapsed * mote.speed * 0.7 + mote.phase) * mote.drift * 2
                twinkle = 0.5 + 0.5 * sin(self.elapsed * 3 * mote.speed + mote.phase * 2)
                arcade.draw_texture_rect(self.glow, arcade.XYWH(x, y, 16, 16), alpha=int(110 * twinkle))
                arcade.draw_circle_filled(x, y, mote.size, (214, 240, 130, int(90 + 160 * twinkle)))
        elif self.condition == "damaged":
            for index, (x, y) in enumerate(self.definition.effect_points):
                if self.spark_flash[index]:
                    strength = self.spark_flash[index] / 0.16
                    arcade.draw_texture_rect(self.glow, arcade.XYWH(x, y, 170 * strength + 40, 170 * strength + 40),
                                             alpha=int(210 * strength))
            for spark in self.sparks:
                fade = 1 - spark.age / spark.lifetime
                arcade.draw_line(spark.x, spark.y, spark.x - spark.vx * 0.03, spark.y - spark.vy * 0.03,
                                 (255, 232, 140, int(255 * fade)), 2)
                arcade.draw_circle_filled(spark.x, spark.y, 1.5, (255, 255, 236, int(255 * fade)))
            if self.flicker:                       # two quick dips per flicker
                dip = 0.5 + 0.5 * sin(self.flicker * 38)
                arcade.draw_lbwh_rectangle_filled(0, 0, self.width, self.height,
                                                  (10, 14, 26, int(70 * dip)))
        else:
            if self.style == "warm":               # dust in warm light
                for mote in self.motes:
                    x = mote.x + sin(self.elapsed * mote.speed + mote.phase) * mote.drift * 2
                    y = mote.y + self.elapsed * 3 * mote.speed % 30 + cos(mote.phase) * 6
                    twinkle = 0.5 + 0.5 * sin(self.elapsed * mote.speed * 2 + mote.phase)
                    arcade.draw_circle_filled(x, y, mote.size, (255, 244, 206, int(40 + 90 * twinkle)))
            for x, y, age in self.glints:          # four-point star that opens and closes
                size = sin(age / 0.7 * pi) * 9
                alpha = int(235 * sin(age / 0.7 * pi))
                arcade.draw_line(x - size, y, x + size, y, (255, 255, 255, alpha), 1.5)
                arcade.draw_line(x, y - size, x, y + size, (255, 255, 255, alpha), 1.5)
                arcade.draw_circle_filled(x, y, 1.5, (255, 255, 255, alpha))
