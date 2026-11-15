"""Encounter rules and timing, independent of Arcade and drawing.

GameView supplies foot positions and inventory, then consumes messages/sounds.
Ghosts own their stolen food until recovery or escape. The blocker is the
only solid enemy. Vampire warnings last two seconds before a single sweep.
"""
from dataclasses import dataclass
from math import hypot, isfinite

from restaurant.hazards.navigation import BLOCKER_SIZE, safe_blocker_position

WARNING_SECONDS = 2.0
STUN_SECONDS = 0.8
GHOST_REACH = 76.0


@dataclass
class Ghost:
    x: float
    y: float
    state: str = "warning"
    remaining: float = WARNING_SECONDS
    food: tuple = ()


@dataclass
class Blocker:
    x: float
    y: float
    state: str = "warning"
    remaining: float = WARNING_SECONDS


@dataclass
class Vampire:
    x: float
    y: float
    direction: int
    state: str = "warning"
    remaining: float = WARNING_SECONDS
    hit: bool = False


class Encounters:
    def __init__(self, day_index, walls, stations, plate):
        self.day_index = day_index
        self.walls = tuple(walls)
        self.stations = tuple(stations)
        self.plate = plate
        self.elapsed = 0.0
        self.misses = 0
        self.ghost = self.blocker = self.vampire = None
        self.ghost_pending = False
        self.ghost_cooldown = 0.0
        self.blocker_count = 0
        self.blocker_cooldown = 0.0
        self.next_vampire = 36.0 - day_index * 3
        self.sweeps = 0
        self.stun = 0.0
        self.flash = 0.0
        self.burst = None                  # (x, y, colour name, seconds left)
        self.events = []                  # (sound cue, player-facing message)

    @property
    def blocker_rectangle(self):
        b = self.blocker
        return (b.x, b.y, *BLOCKER_SIZE) if b and b.state == "blocking" else None

    def missed_order(self):
        self.misses += 1
        if self.misses % 2 == 0 and self.ghost is None:
            self.ghost_pending = True

    def emit(self, cue, message):
        self.events.append((cue, message))

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def clear(self):
        self.ghost = self.blocker = self.vampire = None
        self.ghost_pending = False
        self.stun = self.flash = 0.0
        self.burst = None
        self.events.clear()

    def ghost_in_reach(self, player):
        g = self.ghost
        return bool(g and g.state != "warning" and hypot(g.x - player[0], g.y - player[1]) <= GHOST_REACH)

    def reclaim(self, inventory, player):
        if not self.ghost_in_reach(player):
            return None
        g = self.ghost
        result = inventory.restore_stolen_food(g.food)
        if result.success:
            self.burst = (g.x, g.y + 48, "ghost", 0.6)
            self.ghost = None
            self.emit("ghost_recover", result.message if g.food else "Ghost banished! The plate is safe.")
        else:
            self.emit("reject", result.message)
        return result

    def update(self, dt, inventory, player):
        if not isfinite(dt) or dt < 0:
            raise ValueError("Encounter time must be finite and nonnegative")
        # Fixed short steps make warning transitions and sweep collisions safe
        # even when the window briefly stalls. No timer skips a warning phase.
        remaining = dt
        if not dt:
            self._step(0.0, inventory, player)
        while remaining > 1e-8:
            step = min(remaining, 1 / 30)
            self._step(step, inventory, player)
            remaining -= step

    def _step(self, dt, inventory, player):
        self.elapsed += dt
        self.stun = max(0.0, self.stun - dt)
        self.flash = max(0.0, self.flash - dt)
        self.ghost_cooldown = max(0.0, self.ghost_cooldown - dt)
        self.blocker_cooldown = max(0.0, self.blocker_cooldown - dt)
        if self.burst:
            x, y, kind, left = self.burst
            self.burst = (x, y, kind, left - dt) if left > dt else None
        if self.ghost_pending and not self.ghost and not self.ghost_cooldown:
            self.ghost_pending = False
            self.ghost = Ghost(-60 if self.plate[0] < 480 else 1020, self.plate[1])
            self.emit("ghost_warning", "Two orders missed. A hungry ghost is coming for any food left on the plate!")
        limit = max(0, self.day_index - 1)   # day 3: once, day 4: twice
        if (self.blocker is None and self.blocker_count < limit and not self.blocker_cooldown
                and self.misses >= (self.blocker_count + 1) * 2):
            point = safe_blocker_position(self.walls, self.stations, player)
            self.blocker_cooldown = 5.0
            if point:
                self.blocker = Blocker(*point)
                self.emit("blocker_warning", "An impatient guest is stopping here. Use the other aisle!")
        if self.day_index >= 1 and self.vampire is None and self.elapsed >= self.next_vampire:
            lane = min((210.0, 414.0), key=lambda y: abs(y - player[1]))
            direction = 1 if self.sweeps % 2 == 0 else -1
            self.vampire = Vampire(-70 if direction == 1 else 1030, lane, direction)
            self.sweeps += 1
            self.emit("vampire_warning", "Vampire sweep! Step out of the red lane.")
        self._ghost_step(dt, inventory)
        self._blocker_step(dt, player)
        self._vampire_step(dt, player)

    def _ghost_step(self, dt, inventory):
        g = self.ghost
        if not g:
            return
        if g.state == "warning":
            g.remaining -= dt
            if g.remaining <= 0:
                g.state = "approach"
            return
        if g.state == "approach":
            dx, dy = self.plate[0] - g.x, self.plate[1] - g.y
            distance = hypot(dx, dy)
            if distance <= 150 * dt + 1:
                g.x, g.y = self.plate
                g.food = inventory.steal_docked_food()
                g.state, g.remaining = "flee", 0.65
                self.emit("ghost_steal", "The ghost stole your food! Catch it and press E." if g.food
                          else "Nothing left out to steal. The ghost is leaving.")
            else:
                g.x += dx / distance * 150 * dt
                g.y += dy / distance * 150 * dt
        else:
            g.remaining -= dt
            if g.remaining <= 0:
                g.x += (125 if self.plate[0] >= 480 else -125) * dt
            if g.x < -75 or g.x > 1035:
                self.emit("ghost_steal", "The ghost escaped with the food." if g.food else "The ghost drifted away.")
                self.ghost = None
                self.ghost_cooldown = 15.0

    def _blocker_step(self, dt, player):
        b = self.blocker
        if not b:
            return
        b.remaining -= dt
        if b.remaining > 0:
            return
        if b.state == "warning":
            # Recheck at materialisation: the chef may have entered the marker.
            if safe_blocker_position(self.walls, self.stations, player, (b.x, b.y)):
                b.state, b.remaining = "blocking", 11.0
                self.blocker_count += 1
                self.burst = (b.x, b.y, "dust", 0.55)
                self.emit("blocker_arrive", "The guest is blocking this aisle for 11 seconds. Go around him.")
            else:
                self.blocker = None
                self.blocker_cooldown = 5.0
        else:
            self.burst = (b.x, b.y, "dust", 0.55)
            self.blocker = None
            self.blocker_cooldown = 18.0
            self.emit("blocker_arrive", "The guest moved on. The aisle is clear.")

    def _vampire_step(self, dt, player):
        v = self.vampire
        if not v:
            return
        if v.state == "warning":
            v.remaining -= dt
            if v.remaining <= 0:
                v.state = "sweep"
                self.emit("vampire_sweep", "Vampire passing through - keep clear!")
            return
        old_x = v.x
        v.x += v.direction * (330 + self.day_index * 15) * dt
        if (not v.hit and abs(player[1] - v.y) < 27
                and min(old_x, v.x) - 34 <= player[0] <= max(old_x, v.x) + 34):
            v.hit = True
            self.stun, self.flash = STUN_SECONDS, 0.22
            self.burst = (*player, "bite", 0.5)
            self.emit("vampire_bite", "Bitten! Briefly stunned - keep moving once the stars clear.")
        if v.x < -90 or v.x > 1050:
            self.vampire = None
            self.next_vampire = self.elapsed + (44 - self.day_index * 5)
