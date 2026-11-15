# Classic Chef

Classic Chef is a four-day restaurant game. Run `python main.py` after installing
`requirements.txt`. On Windows, the playable ZIP includes Python and Arcade.

Move with WASD or the arrow keys. Press E at the service hatch to open service,
then read the order cards. E at the plate island picks up the plate even when it
is empty. Press E at a pantry box while carrying the plate to add the ingredient
directly, or collect a single ingredient by hand and put it on the docked plate.
The chef holds the plate in his hands and has walking and standing poses in
all four directions.

- Tomato sandwich uses one sandwich and one tomato. To chop the tomato, bring
  it by hand or on the plate and press E at the board. The chef cuts it for a
  moment. Press E again to collect the pieces. Either form works in the recipe.
- Pasta uses one noodles, one milk and one tomato. Load the pot one ingredient
  at a time or supply all three with the carried plate. Cooking takes four
  seconds. Bring an empty carried plate to collect the pasta.
- Press E at the hatch to serve the matching order. Single sandwich and milk
  orders also accept the item by hand. The chef keeps the plate after delivery.
- Serving earns 100 gold, plus a 50 gold bonus within 30 seconds. Once you have
  at least 200 gold that day, return the plate and press Enter to advance. The
  fourth day opens the ending screen.
- Q removes the most recently added portion from the docked plate into empty
  hands. E at the bin discards held food first, then clears food from the plate.
- P pauses, M toggles sound, R restarts, F1 shows the collision footprints and
  Esc closes the game.

The kitchens use shared furniture with a palette change and swapped islands in
the silver rooms, plus vines, cracks and rust in the worn versions. The day
definitions in `restaurant/kitchen/days.py` are the integration points for the
environment member's final artwork and layouts.

The stages are Warm Kitchen, Silver Kitchen, Overgrown Kitchen and Damaged
Silver Kitchen. Up to three order cards can be active. A new order arrives
after five to ten seconds when space is available. Each order expires after two
minutes. A rejected delivery preserves the plate and gold. Sound effects are
original synthesized WAV files under `assets/audio`.

Run `python -m pytest -q` and `python main.py --self-test artifacts/check` on a
Windows desktop. The game uses a local graphics context. The full playthrough
test exercises chopping, carrying, cooking, serving and plate return across all
four days.
