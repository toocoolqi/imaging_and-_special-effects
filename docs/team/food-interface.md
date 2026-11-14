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

The first E at the service table calls `OrderSystem.start()` and starts one
two-minute order. Additional orders arrive after a random wait of 5 to 10 seconds while there is
room for them, up to three active orders.
Serving within the first 30 seconds adds 50 points to the usual 100.

At service, pass the carried plate snapshot and the food system to
`OrderSystem.try_serve(plate, food)`. It checks the oldest accepted exact match,
then consumes that revision through `food.serve_plate(revision)` before changing
orders or score. All of this runs synchronously in one Arcade update. The same
plate returns to the carried state empty.

The scene adapter draws food and cookware from snapshots. GameView routes sound
cues and controls the bubble loop based on cooking, visibility, pause, and mute.
