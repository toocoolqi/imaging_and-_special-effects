# Player integration notes

## Who owns what

Member 1 owns `restaurant/player`, input routing in `GameView`, and chef frames.
Member 2 can connect ingredients/plates through the selected `InteractionTarget`.
Member 3 can connect the serving action and draw the order sidebar. Neither
system should move the chef or read the controller's private variables.

The earlier team guides describe the eventual full game. The shared foundation
now includes all agreed snapshot/result records in `restaurant/shared/contracts.py`.
Task2 ingredients/plates are now implemented and composed by GameView.
See TEAM_PLAN.md for the current role split and next cooking/order milestone.

## Public interface

| Interface | Meaning |
| --- | --- |
| `PlayerController(spawn)` | Create one chef at an `(x, y)` world position |
| `set_move_key(direction, pressed)` | Set canonical `up/down/left/right` input |
| `update(delta_time, walls)` | Move, collide and animate; call once per update |
| `position` | Read-only `(x, y)` chef center |
| `ground_position` | Foot center, 32 pixels below `position`; use for depth/shadows |
| `direction` | Read-only facing; retained while idle |
| `state` / `is_moving` | `idle` or `walk` / whether actual movement occurred |
| `sprite` | Arcade sprite; add to a SpriteList for drawing |
| `clear_input()` | Stop and clear held movement on focus loss/pause |
| `reset(spawn)` | Clear input, return to spawn, face down |
| `choose_target(position, targets, radius=64.0)` | Return nearest target or `None` |

`InteractionTarget(target_id, kind, x, y, ingredient_id=None)` is immutable.
Kinds are `box`, `plate`, `bin`, `serve`, and `chop`. Box ingredient IDs are `sandwich`,
`tomato`, `noodles`, and `milk`. Other target kinds must leave ingredient_id empty.
Target IDs must be unique. Range includes exactly 64 pixels, uses Euclidean
distance, and resolves ties alphabetically by ID. Facing is not required.

## Connect a scene

```python
from restaurant.player.controller import PlayerController
from restaurant.player.interaction import choose_target

# During scene setup:
self.player = PlayerController((450, 170))
self.players.append(self.player.sprite)  # your arcade.SpriteList

# In the scene's on_update(delta_time):
self.player.update(delta_time, self.walls)
target = choose_target(self.player.position, self.targets)

# In the scene's on_draw():
self.players.draw(pixelated=True)
```

Keep the existing physical-key handling in `GameView`: it allows W and Up to be
held together, ignores key-repeat, and clears input on pause/reset/focus loss.
Do not also call `players.update()` or `player.sprite.update()`; the controller
already owns movement. Do not start another Arcade window for a teammate's system.

## Connect interactions

`GameView.handle_interaction(action, target)` is the replaceable routing hook.
It runs after movement, once per queued E/Q press. Its current implementation
only displays feedback. When the other systems exist, replace that method's
demo feedback with calls to their public APIs:

| Action and target | Future call |
| --- | --- |
| `interact` + box | `ingredients.collect(target.ingredient_id)` |
| `interact` + plate | `ingredients.add_to_plate()` |
| `remove` + plate | `ingredients.remove_from_plate()` |
| `interact` + bin | `ingredients.discard()` |
| `interact` + serve | Submit a plate snapshot through the agreed serving flow |
| `interact` + chop | Reserved cutting-system entry point; currently feedback only |
| No target / remove away from plate | Show feedback; mutate no state |

For future serving, advance order timers first, take `ingredients.snapshot().plate`,
call `orders.try_serve(plate)`, then clear that exact revision only after success,
as described in the original member guides. Keep those calls together in the
scene. Ingredient state belongs to Member 2; order state belongs to Member 3.
The player module does not need to change. No held-item animations are included.

The sidebar is `(left=960, bottom=0, width=256, height=704)` in world coordinates. Replace the demo's
sidebar drawing with Member 3's renderer when it is ready. Keep player feedback
somewhere visible. Reset/pause must eventually cover all systems together.

## Collision and layout rules

- Coordinates start at bottom-left. Kitchen width is 960 and height is 704.
- Furniture pictures, solids and approaches share `restaurant/kitchen/layout.py`.
  `WALL_RECTANGLES`/`TARGETS` remain available through shared settings.
  Read [kitchen notes](kitchen_layout.md) before changing this map.
- The camera scales the whole 1216 x 704 scene without stretching. The resizable
  startup window accounts for Windows DPI and monitor work area; see
  `restaurant/display.py`. Movement and collisions use world pixels. Text uses
  a separate screen camera and displayed font size, so resizing keeps it legible.
- Add solid, static, axis-aligned wall/counter sprites to `self.walls`.
  The same SpriteList can be edited when the layout changes. Replacing the list
  is supported too. Rotated/moving obstacles are outside this demo's contract.
- Spawn the chef on clear floor. Reset does not search for a free spawn point.
- The fixed foot hitbox is 32 by 20 world pixels, centered 32 pixels below the
  sprite center. It stays identical across animations. F1 shows it. The chef
  center remains the interaction origin. Furniture uses its measured base,
  while drawing order uses feet so raised counters can occlude the chef.
- Motion uses 200 pixels per second, normalized diagonals, and Arcade's
  PhysicsEngineSimple with steps no longer than 2 pixels to prevent tunneling.
  A stalled update consumes at most 0.25 seconds of movement/animation; excess
  time is intentionally discarded. Normal update rates retain equal speed.
- Collision uses actual displacement to choose walk versus idle. Pressing into
  a wall turns the chef toward it but stops walking when movement is blocked.
- Place interaction points on accessible floor beside their counters. The
  selection helper does **not** perform line-of-sight or pathfinding checks.
  If you change the layout, ensure another wall cannot separate the chef from
  a point within 64 pixels. The included layout satisfies this placement rule.
- Change layout/scale/constants in shared settings only with team agreement.

## Animation choices

Four source walking frames are used for each direction in row-major order.
The front-facing source idle pose is used for down. Other idle directions freeze
the first walking frame because the supplied image has no separate directional
idle columns. Animation runs at one frame per 0.14 seconds while moving.

The presentation image does not provide a clean native 32x32 grid despite its
heading. Prepared frames preserve the supplied artwork in a 56x92 transparent
canvas, displayed at scale 1.0. Replacing art later requires only matching these
frame names/canvas alignment or adjusting the loader and stable collision size.
