# Classic Chef

Classic Chef is a four-day restaurant game. Run `python main.py` after installing
`requirements.txt`. On Windows, the playable ZIP includes Python and Arcade.

Move with WASD or the arrow keys. At the service hatch, press E with empty hands to
accept the ticket. Prepare the food, press E at the plate island to put it on the
plate, then press E again to pick up the loaded plate. Serve at the hatch and
return the empty plate to the island.

- Tomato sandwich uses one sandwich and one tomato.
- Creamy noodles uses one noodles and one milk. Put both in the pot, wait four
  seconds, collect the cooked portion and plate it.
- A correct plate earns 100 gold. At 200 gold, return the plate and press Enter.
  The fourth day opens the ending screen.
- Q removes the most recently added portion from the docked plate into empty
  hands. E at the bin discards held food first, then food on the docked plate.
- P pauses, M toggles sound, R restarts, F1 shows the collision footprints and
  Esc closes the game.

The kitchens use shared furniture with a palette change and swapped islands in
the silver rooms, plus vines, cracks and rust in the worn versions. The day
definitions in `restaurant/kitchen/days.py` are the integration points for the
environment member's final artwork and layouts.

The four exact stage names are Warm Kitchen, Silver Kitchen, Overgrown Kitchen
and Damaged Silver Kitchen. The single ticket expires after 60 seconds and the
same recipe becomes available again. A rejected delivery preserves the plate and
gold. Sound effects are original synthesized WAV files under `assets/audio`.

Run `python -m pytest -q` and `python main.py --self-test artifacts/check` on a
Windows desktop. The game uses a local graphics context. The full playthrough
test exercises the hatch, plate return, the two recipes and all four days.
