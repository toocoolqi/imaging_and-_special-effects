# Food integration interfaces

GameView owns station routing and advances both systems before processing queued
inputs. The stove target is `pot` (kind `pot`). Food snapshots expose the held
food, physical plate location, and pot stage and time. `pasta` is a dish
ID accepted in plate and order snapshots and never at a raw ingredient crate.

Pantry pickup adds directly to a carried plate when it has room. Pickup with
empty hands still holds one ingredient for the docked plate or pot. At the
stove, a carried plate supplies one of each recipe ingredient still needed.
Extra items stay on the plate. Collecting ready pasta requires an empty
carried plate.

Orders are live the moment they arrive: their timer starts at once. The first
arrives when the day starts; more follow every 14 to 7.5 seconds depending on
the day (see `restaurant/kitchen/days.py`), up to three on screen. Each order
pays its base price plus a speed tip that shrinks while the customer waits;
the day ends at its gold target.

At service, pass the carried plate snapshot and the food system to
`OrderSystem.try_serve(plate, food)`, or call `try_serve_held(food)` for a
sandwich or milk in hand. It checks the oldest exact match, then
consumes that revision through `food.serve_plate(revision)` before changing
orders or gold. All of this runs synchronously in one Arcade update. The same
plate returns to the carried state empty.

The scene adapter draws food and cookware from snapshots. GameView routes sound
cues and controls the bubble loop based on cooking, visibility, pause, and mute.
