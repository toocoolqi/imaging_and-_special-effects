# Member 2 — Food, cooking, plates, sidebar orders and sound

Read [TEAM_PLAN.md](../TEAM_PLAN.md). Your task2 code and sprites are now the
shared food foundation. Extend it rather than creating a competing inventory.
You own the complete small gameplay loop below, not only sprite extraction.

## What is already available

restaurant/ingredients/system.py owns one held ingredient and a four-item plate.
Its public methods are collect, add_to_plate, remove_from_plate, discard,
snapshot, clear_plate(expected_revision) and reset. The combined kitchen routes
E/Q into these methods. The independent lab runs with:

    python -m demos.ingredients_demo

assets/ingredients/sprites contains sandwich, tomato, noodles, milk, matching
boxes, plate, pot_empty, pot_cooking and pot_cooked. These are the approved food
IDs. The cooking pictures are available but cooking behavior is not implemented.
The plate is currently stationary; physical plate transport is your next step.

## Files and ownership

Use restaurant/ingredients/ for food, plate lifecycle and pot state;
restaurant/orders/ for order generation, acceptance, timers, matching and stats;
assets/orders/ for recipe icons; assets/audio/ and a small restaurant/audio.py
for Arcade sound effects. Update shared contracts with Member 1 first.
IngredientRenderer remains usable in its independent lab. Connect the combined
room through the existing scene adapter; do not draw another set of crates over
it or move the chef from your food system.

## Implement this minimum flow in order

1. Keep pickup/add/remove/discard working and enforce a single occupied hand.
   A failed action leaves the complete state unchanged and explains why.
2. Make the plate a reusable physical object with exactly three locations:
   DOCKED at its home table, CARRIED by the chef, or temporarily AT_SERVICE while
   a single serve attempt resolves. There is one plate, not an infinite supply.
   Holding a plate and holding an ingredient are mutually exclusive.
3. At the plate table: E with held food adds it if the plate is docked. Q with
   empty hands removes the most recent food. E with empty hands picks up the
   docked plate (empty or prepared). E while carrying that plate returns it to
   its home table with its contents intact. At a crate, a carried plate prevents
   pickup and gives feedback. R restores the plate at home and empties hands.
4. Add a pot interaction at the stove. E with held noodles/milk deposits that
   item only if allowed and clears the hand only on success. Use this default
   recipe for a small demonstrable loop: one noodles + one milk, cooking for
   4 seconds. Reject duplicates, sandwich and tomato without losing them.
   Keep recipe/timer values in one data definition so they can change later.
5. Pot states: EMPTY → LOADING → COOKING → READY → EMPTY. Start the timer when
   the required ingredients are present. Show pot_empty/loading, pot_cooking
   with looping bubbles/steam, then pot_cooked for READY. Use Arcade time-based
   updates, not sleeping or a new thread; pause freezes timers and animation.
   No burning or complex recipes are required for this milestone.
6. At a READY pot, E with empty hands takes a cooked portion, emptying the pot.
   Put that portion onto the docked plate with E. A full hand/plate must not
   delete the cooked result. Introduce a distinct DishId such as creamy_noodles
   and a typed held-item union; do not pretend it is a raw IngredientId or pass
   it through validators that currently permit only the four raw ingredients.
   Update immutable snapshots, validation and both systems' tests together.
7. Draw the carried plate/food as a small attached visual using the current chef
   frames. Do not add held-item character animations. The plate should disappear
   from its home table only while being carried and reappear on return.
8. Build the order sidebar and service flow described next.

## Sidebar and serving rules

Show up to three order cards. Each card has an ID, recipe name, ingredient/dish
icons and quantities, remaining time and a status. Use a fixed initial recipe
list with at least Tomato sandwich (sandwich + tomato) and Creamy noodles
(cooked creamy_noodles portion). Match exact quantities, regardless of placement
order; reject missing, extra or raw substitutes. Counters preserve duplicates.

Start with one pending order at launch. E at the service hatch with empty hands
accepts the oldest pending order and starts its 60-second timer. This makes
accepting/taking an order a visible action. Show pending vs accepted clearly.
Use an explicit incrementing order ID and create a replacement pending order
when one completes/expires, never exceeding three cards.

E at the hatch while carrying a prepared plate attempts the oldest accepted
matching order. On success: complete once, add 100 score, increase completed
count, remove only that order, clear FOOD from that exact plate revision, and
keep the EMPTY PLATE IN THE CHEF'S HANDS. Show a brief outgoing-dish effect at
the hatch. The player must walk the empty plate back and E to dock it before
preparing the next dish. The whole plate must not disappear or teleport home.

On failure (no accepted order, wrong recipe, empty plate or timeout), preserve
plate/food/score and show feedback. Process timer expiry before serving in that
frame. An expired order increments expired once and never completes later.
Acceptance increments accepted only once. Display accepted/completed/expired
counts and score. Make serving and plate clearing one transaction guarded by
plate revision; key repeat or stale snapshots must never award twice.

## Sound essentials

Use arcade.load_sound/play_sound and bundled WAV/OGG files. Include short sounds
for pickup, plating, returning a plate, accepting an order, successful serving,
rejected action and a soft pot bubble loop. Start the loop once on COOKING;
stop it on READY, pause, reset and leaving the scene. Do not start a new sound
every frame. Provide a visible mute control (M), retain volume preferences on
session reset, and keep cues quiet enough to hear success/error separately.
List audio sources/licenses or state that you created them. No network audio
or optional missing assets in the final playable build.

## Public methods and tests

Keep existing food methods compatible where possible. Add explicit methods for
pickup_plate, return_plate, add_to_pot, take_cooked_portion, update(dt), and
immutable plate/pot snapshots. OrderSystem should expose update, accept_next,
try_serve and snapshot/stats. Coordinate final signatures with Member 1 in a
short interface note before editing GameView. Renderers only read snapshots.

Test successful and blocked pickup, four-item capacity, duplicate quantities,
pot recipe/4-second transition, pause, taking READY food, full hands, plate
pickup/return, exact matches, timeout priority, stale revision, double serving,
retained empty plate, reset, mute and sound-loop stopping. Then demonstrate two
orders consecutively in the combined game, including carrying the same plate
back between them. Deliver code, tests, audio/license notes and a short recording
or screenshots. Sidebar, pots, serving and sounds must work in the main game,
not only your standalone lab.
