"""World-space feedback for order events: coins, floating gold, shake, confetti.

Everything here is presentation. Each effect is triggered by ONE event
(a plate served, a wrong plate, an order expiring, the day ending) and then
runs on delta time until it finishes, so pausing the game freezes it.

Techniques
- Particle system: every particle has position, velocity, age and lifetime;
  update() integrates motion, draw() fades by age, dead ones are removed.
  Same structure as the Week 9 SmokeParticle, with gravity instead of lift.
- Screen shake: a random camera offset that decays to zero (Week 10).
- Additive-looking glow: a soft radial texture drawn with pulsing alpha
  (Week 8 lighting).
"""
from math import cos, pi, sin
import random

import arcade

GOLD = (250, 204, 78)
GOLD_DARK = (176, 128, 36)
CONFETTI = ((250, 204, 78), (104, 214, 150), (236, 88, 78), (110, 170, 240), (240, 240, 236))


class Particle:
    def __init__(self, kind, x, y, vx, vy, lifetime, size, color, gravity=0.0, floor=None):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.lifetime, self.size, self.color, self.gravity = lifetime, size, color, gravity
        self.floor = floor          # y where a coin bounces, or None
        self.age = 0.0
        self.spin = random.uniform(0, 2 * pi)
        self.spin_speed = random.uniform(8, 16)

    @property
    def is_dead(self):
        return self.age >= self.lifetime

    def update(self, dt):
        self.age += dt
        self.vy -= self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.spin += self.spin_speed * dt
        if self.floor is not None and self.y < self.floor and self.vy < 0:
            self.y = self.floor
            self.vy *= -0.45         # lose energy on each bounce
            self.vx *= 0.7

    def draw(self):
        progress = min(1.0, self.age / self.lifetime)
        alpha = int(255 * (1.0 - progress ** 3))
        if self.kind == "coin":      # a spinning coin: its width follows |cos|
            width = max(1.5, self.size * abs(cos(self.spin)))
            arcade.draw_ellipse_filled(self.x, self.y, width * 2, self.size * 2, GOLD_DARK + (alpha,))
            arcade.draw_ellipse_filled(self.x, self.y, max(1, width * 2 - 3), self.size * 2 - 3,
                                       GOLD + (alpha,))
        elif self.kind == "confetti":
            w = self.size * abs(cos(self.spin)) + 1
            arcade.draw_rect_filled(arcade.XYWH(self.x, self.y, w, self.size * 0.6),
                                    self.color + (alpha,), tilt_angle=self.spin * 20)
        else:                        # "spark": shrinks as it fades
            arcade.draw_circle_filled(self.x, self.y, max(0.5, self.size * (1 - progress)),
                                      self.color + (alpha,))


class FloatingText:
    def __init__(self, value, x, y, color, size=18, lifetime=1.4):
        self.value, self.x, self.y, self.color, self.size = value, x, y, color, size
        self.lifetime, self.age = lifetime, 0.0

    @property
    def is_dead(self):
        return self.age >= self.lifetime

    def update(self, dt):
        self.age += dt
        self.y += 46 * dt * (1 - self.age / self.lifetime)   # rises, slowing down


class OrderEffects:
    MAX_PARTICLES = 260
    CALL_SECONDS = 3.0      # how long the hatch calls after an order arrives

    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.shake_time = 0.0
        self.shake_strength = 0.0
        self.flash = 0.0                 # red vignette after a mistake
        self.call_time = 0.0             # "!" over the hatch after an arrival
        self.elapsed = 0.0
        self.glow = arcade.make_soft_circle_texture(128, (255, 214, 120), center_alpha=170, outer_alpha=0)
        self._labels: dict[str, arcade.Text] = {}

    def reset(self):
        self.particles.clear()
        self.texts.clear()
        self.shake_time = self.flash = self.call_time = 0.0

    # ------------------------------------------------------------ triggers
    def served(self, x, y, gold):
        """Coins burst out of the hatch and '+gold' floats up."""
        r = self.random
        for _ in range(min(18, 6 + gold // 8)):
            angle = r.uniform(0.2 * pi, 0.8 * pi)
            speed = r.uniform(140, 300)
            self._add(Particle("coin", x + r.uniform(-30, 30), y + 10, cos(angle) * speed,
                               sin(angle) * speed, r.uniform(1.0, 1.5), r.uniform(4.5, 6.5), GOLD,
                               gravity=620, floor=y - r.uniform(40, 70)))
        for _ in range(14):
            angle = r.uniform(0, 2 * pi)
            self._add(Particle("spark", x, y + 16, cos(angle) * r.uniform(60, 190),
                               sin(angle) * r.uniform(60, 190), r.uniform(0.3, 0.6), r.uniform(2, 4),
                               (255, 244, 190)))
        self.texts.append(FloatingText(f"+{gold} G", x, y + 34, GOLD, 22))

    def rejected(self, x, y, message="Wrong dish!"):
        self.shake(0.3, 7)
        self.flash = 0.35
        self.texts.append(FloatingText(message, x, y + 34, (240, 110, 96), 15, 1.1))
        r = self.random
        for _ in range(10):
            angle = r.uniform(0, 2 * pi)
            self._add(Particle("spark", x, y + 12, cos(angle) * r.uniform(50, 150),
                               sin(angle) * r.uniform(50, 150), r.uniform(0.25, 0.45), r.uniform(2, 4),
                               (236, 88, 78)))

    def expired(self, x, y):
        self.shake(0.25, 5)
        self.flash = 0.25
        self.texts.append(FloatingText("Order expired", x, y + 34, (240, 110, 96), 14, 1.3))

    def arrived(self, x, y, recipe_name=""):
        """A burst of light, the order's name and a "!" call at the hatch."""
        self.call_time = self.CALL_SECONDS
        if recipe_name:
            self.texts.append(FloatingText(recipe_name, x, y + 34, (236, 240, 236), 14, 1.4))
        r = self.random
        for _ in range(8):
            angle = r.uniform(0.15 * pi, 0.85 * pi)
            self._add(Particle("spark", x + r.uniform(-40, 40), y + 70, cos(angle) * r.uniform(20, 60),
                               sin(angle) * r.uniform(20, 70), r.uniform(0.4, 0.8), r.uniform(2, 3),
                               (255, 236, 170)))

    def celebrate(self, width, height):
        """Confetti rains over the whole kitchen when the day target is reached."""
        r = self.random
        for _ in range(130):
            self._add(Particle("confetti", r.uniform(20, width - 20), height + r.uniform(0, 260),
                               r.uniform(-40, 40), r.uniform(-150, -60), r.uniform(2.6, 4.6),
                               r.uniform(6, 10), r.choice(CONFETTI), gravity=40))

    def shake(self, seconds, strength):
        self.shake_time = max(self.shake_time, seconds)
        self.shake_strength = max(self.shake_strength, strength)

    def _add(self, particle):
        if len(self.particles) < self.MAX_PARTICLES:
            self.particles.append(particle)

    # ------------------------------------------------------------ frame
    def update(self, dt):
        self.elapsed += dt
        self.flash = max(0.0, self.flash - dt)
        self.call_time = max(0.0, self.call_time - dt)
        self.shake_time = max(0.0, self.shake_time - dt)
        if not self.shake_time:
            self.shake_strength = 0.0
        for item in self.particles:
            item.update(dt)
        for item in self.texts:
            item.update(dt)
        self.particles = [p for p in self.particles if not p.is_dead]
        self.texts = [t for t in self.texts if not t.is_dead]

    @property
    def shake_offset(self):
        """Random camera offset in world pixels; (0, 0) when calm."""
        if self.shake_time <= 0:
            return 0.0, 0.0
        s = self.shake_strength * min(1.0, self.shake_time / 0.15)
        return self.random.uniform(-s, s), self.random.uniform(-s, s)

    def draw_hatch_call(self, x, y, allowed: bool = True):
        """A pulsing light and '!' bubble over the hatch after a new order."""
        if not allowed or self.call_time <= 0:
            return
        fade = min(1.0, self.call_time / 0.5)
        pulse = (0.5 + 0.5 * sin(self.elapsed * 5)) * fade
        arcade.draw_texture_rect(self.glow, arcade.XYWH(x, y + 78, 150 + 40 * pulse, 110 + 30 * pulse),
                                 alpha=int(90 + 120 * pulse))
        bob = sin(self.elapsed * 4) * 3
        cx, cy = x, y + 120 + bob
        arcade.draw_circle_filled(cx, cy, 15, (60, 44, 30))
        arcade.draw_circle_filled(cx, cy, 13, (250, 240, 214))
        arcade.draw_triangle_filled(cx - 5, cy - 11, cx + 5, cy - 11, cx, cy - 20, (250, 240, 214))
        arcade.draw_lbwh_rectangle_filled(cx - 2, cy - 2, 4, 11, (214, 72, 60))
        arcade.draw_lbwh_rectangle_filled(cx - 2, cy - 8, 4, 4, (214, 72, 60))

    def draw(self, text=None, bounds=None):
        """Particles, floating text and the mistake flash. bounds = (w, h)."""
        for particle in self.particles:
            particle.draw()
        for index, item in enumerate(self.texts[-8:]):
            fade = 1.0 - (item.age / item.lifetime) ** 2
            color = item.color + (int(255 * fade),)
            key = f"float_{index}_{item.size}"   # a cached label keeps its font size
            if text is not None:
                text(key + "_s", item.value, item.x + 1, item.y - 2, item.size, (30, 22, 16, color[3]),
                     anchor_x="center", bold=True)
                text(key, item.value, item.x, item.y, item.size, color, anchor_x="center", bold=True)
            else:
                label = self._labels.get(key)
                if label is None:
                    label = self._labels[key] = arcade.Text(item.value, item.x, item.y, color, item.size,
                                                            anchor_x="center", bold=True)
                label.text, label.x, label.y, label.color = item.value, item.x, item.y, color
                label.draw()
        if self.flash and bounds:
            alpha = int(90 * min(1.0, self.flash / 0.2))
            w, h = bounds
            for inset, a in ((0, alpha), (10, alpha // 2)):
                arcade.draw_lbwh_rectangle_outline(inset + 6, inset + 6, w - 12 - inset * 2,
                                                   h - 12 - inset * 2, (236, 60, 50, a), 12)
