"""Conservative floor-route check before adding a temporary solid customer.

All coordinates here are FOOT positions, not sprite centres. Obstacles are
expanded by the chef's 32 x 20 foot collider. A four-way grid leaves a small
clearance and forbids diagonal corner cutting.
"""
from collections import deque
from math import hypot

STEP = 8
BLOCKER_SIZE = (72, 32)
CANDIDATES = ((480, 330), (480, 410), (790, 250), (480, 180), (110, 400))


def routes_open(walls, stations, player, blocker):
    rects = (*walls, blocker)

    def free(point):
        x, y = point
        return not any(abs(x - cx) < w / 2 + 16.25 and abs(y - cy) < h / 2 + 10.25
                       for cx, cy, w, h in rects)

    def connections(point):
        # Link an exact interaction point to nearby grid centres, including
        # stations whose standing spot lies close to a counter edge.
        px, py = point
        gx, gy = round(px / STEP), round(py / STEP)
        result = set()
        for ix in range(gx - 2, gx + 3):
            for iy in range(gy - 2, gy + 3):
                node = (ix * STEP, iy * STEP)
                if node in floor and all(free((px + (node[0] - px) * t / 8,
                                               py + (node[1] - py) * t / 8)) for t in range(9)):
                    result.add(node)
        return result

    floor = {(x, y) for x in range(32, 936, STEP) for y in range(32, 592, STEP) if free((x, y))}
    goals = [connections(point) for point in (player, *stations)]
    if any(not goal for goal in goals):
        return False
    seen = set(goals[0])
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for neighbour in ((x - STEP, y), (x + STEP, y), (x, y - STEP), (x, y + STEP)):
            if neighbour in floor and neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return all(goal & seen for goal in goals)


def safe_blocker_position(walls, stations, player, preferred=None):
    candidates = (preferred,) if preferred else CANDIDATES
    for x, y in candidates:
        if hypot(x - player[0], y - player[1]) < 110:
            continue
        if any(hypot(x - sx, y - sy) < 85 for sx, sy in stations):
            continue
        w, h = BLOCKER_SIZE
        if any(abs(x - cx) < (w + rw) / 2 + 8 and abs(y - cy) < (h + rh) / 2 + 8
               for cx, cy, rw, rh in walls):
            continue
        if routes_open(walls, stations, player, (x, y, w, h)):
            return x, y
    return None
