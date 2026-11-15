# Classic Chef

Classic Chef is a four-day restaurant game. Run `python main.py` after installing
`requirements.txt`. On Windows, the playable ZIP includes Python and Arcade.

The app starts at the main menu. Click **Play** or press **Enter** to open the
first kitchen. Click **Quit** or press **Esc** to leave the menu.

Move with WASD or the arrow keys. Orders come in by themselves: a bell rings,
a "!" flashes over the service hatch and a card slides into the sidebar with
its timer already running. E at the plate island picks up the plate even when it
is empty. Press E at a pantry box while carrying the plate to add the ingredient
directly, or collect a single ingredient by hand and put it on the docked plate.
The chef holds the plate in his hands and has walking and standing poses in
all four directions.
Single ingredients lift into the palm when picked up and follow the moving
hand. Fingers overlap the food, and the chef's body hides it when facing away.

- Tomato sandwich uses one sandwich and one tomato. To chop the tomato, bring
  it by hand or on the plate and press E at the board. The chef cuts it for a
  moment. Press E again to collect the pieces. Either form works in the recipe.
- Pasta uses one noodles, one milk and one tomato. Load the pot one ingredient
  at a time or supply all three with the carried plate. Cooking takes four
  seconds. Bring an empty carried plate to collect the pasta.
- Lunch set uses one sandwich and one milk on the plate.
- Press E at the hatch to serve the matching order. Single sandwich and milk
  orders also accept the item by hand. The chef keeps the plate after delivery.
  A plate nobody ordered is sent back with a buzz and a shake; nothing is lost.
- Each order pays its base price (sandwich or milk 30, lunch set 50, tomato
  sandwich 60, pasta 90) plus a speed tip of up to 30 gold that shrinks while
  the customer waits. An order that runs out of time pays nothing.
- Each day is busier than the last: order timers of 82, 68, 56 and 45 seconds,
  a new order about every 14, 11, 9 and 7.5 seconds, and gold targets of 150,
  220, 290 and 360 (so more orders to serve), never more than three on screen.
  When the target is reached the day is complete: return the plate and press
  Enter to open the next kitchen. The fourth day opens the ending screen.
  Number keys 1-4 jump straight to a day.
- The compact sidebar clock counts down the whole shift: 3:00, 2:45, 2:30
  and 2:15 across the four days. Reach that day's gold target before zero or
  the shift fails. Enter or R retries that kitchen, keeping only earlier days'
  gold. Reaching the target stops the deadline and enemies, leaving time to
  return the plate. P freezes the clock along with the rest of the game.
- Two missed orders attract a floating ghost. It takes food only from a
  plate left on its table. Catch it and press E to put the food back on your
  plate, or banish it before it steals. If it escapes offscreen the food is
  lost. Make space if your plate has filled up while chasing it.
- On days 3 and 4, missed orders can summon a stocky guest who blocks an
  aisle for 11 seconds. There is a warning marker before he appears, and
  every station keeps an alternative route. He appears at most once on
  day 3 and twice on day 4.
- From day 2, a vampire sometimes crosses a marked red lane. Move above or
  below the lane during its two-second warning. One bite briefly stops the
  chef for 0.8 seconds with stars, a flash and sound; food is never removed.
  Cooking and order timers continue, so dodge it when possible.
- Q removes the most recently added portion from the docked plate into empty
  hands. E at the bin discards held food first, then clears food from the plate.
- P pauses, M toggles sound, R restarts, F1 shows the collision footprints and
  Esc closes the game.

The four days follow the story: Day 1 Overgrown Kitchen (an abandoned
restaurant), Day 2 Warm Kitchen (the same room restored with that gold), Day 3
Damaged Silver Kitchen (a second, run-down kitchen) and Day 4 Silver Kitchen
(renovated). Each has its own art set in `assets/kitchen/<map_id>/`; twins share
every footprint and station, and the silver rooms swap the islands. Order
difficulty per day (target, patience, arrival rate, menu) is in
`restaurant/kitchen/days.py`.

The chef now walks at 230 world pixels per second (previously 200), with
equal diagonal speed and stable collision stopping. Encounter timing, asset
placement and public hooks are explained in [SHIFT_AND_ENEMIES.md](SHIFT_AND_ENEMIES.md).

Up to three orders can be on screen at once. Each shows a timer bar that turns
amber then red and blinks under 10 seconds with a tick; a new card glows gold
for a moment when it arrives. Effects: coins and the
gold earned float up from the hatch, the gold meter counts up, expired cards
turn grey and shake, mistakes shake the camera, confetti marks a finished day
and a fade leads into the next kitchen. The overgrown room drips into its
puddles, the damaged steel room sparks and flickers, and each restaurant has
its own background music. Sounds are original synthesized WAV files under
`assets/audio`.

Run `python -m pytest -q` and `python main.py --self-test artifacts/check` on a
Windows desktop. The game uses a local graphics context. The full playthrough
test exercises chopping, carrying, cooking, serving and plate return across all
four days.

Art and the chef use a shared pixel grid; labels remain clear at screen
resolution. The window accounts for Windows scaling and stays within the
desktop. Fixed wall equipment cannot be approached from behind. The center
islands still allow natural walking and overlap around their sides and backs.
