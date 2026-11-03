# Member 1 — Player and integration

Read [TEAM_PLAN.md](../TEAM_PLAN.md) first. Your job is to make the other two
members' work run together as one usable Arcade game.

## Starting point

Keep restaurant/player/controller.py as the movement owner. It already handles
idle/facing, equal diagonal speed, fixed 32 x 20 foot collision, substeps and
focus loss. ground_position is 32 pixels below the sprite center; position
remains the interaction origin. There are no hold-item animations to add.

The shared kitchen already calls IngredientSystem's public methods in
GameView.handle_interaction. Do not duplicate its held item or plate list.
The small held-food icon is visual feedback, not a new animation state.

## Files you own

- restaurant/player/ and tests/test_player.py: input, movement and animation.
- restaurant/game_view.py: composition, map selection and action routing.
- restaurant/display.py: sizing, cameras and readable UI after resizing.
- restaurant/kitchen/scene.py: map rendering and depth integration, coordinated
  with Member 3. Member 3 owns the environment definitions/art.
- tests/test_combined_game.py and restaurant/demo_check.py: real user flows.
- PlayerDemo.spec and README.md: final packaging and accurate controls.

## Work in this order

1. Accept Member 3's map data through a KitchenDefinition-like record containing
   room size, spawn, props, footprints, wall decorations and station targets.
   Provide all four map IDs: warm_clean, warm_overgrown, metal_clean,
   metal_damaged. Avoid four copies of GameView or PlayerController.
2. Replace global room-size assumptions with the active definition. Both camera
   projection and movement bounds must change with the room. Keep the sidebar
   outside the floor. Keep the current DPI/work-area startup behavior.
3. Provide a small in-game map selector or number-key selection (1–4 when no
   menu is active). Clear held movement when changing map. For this milestone,
   changing map starts a fresh session: reset food, pots, orders and plate home.
   Show this rule in the selector so progress is not lost unexpectedly.
4. Ask Member 2 for public cooking, plate-transport and order APIs. Route one E
   intent per physical press through them. Keep Q as plate removal and P/R as
   pause/reset. Pause freezes movement, pot timers, bubbles, order timers and
   looping sounds; reset clears all state. Losing focus clears input.
5. Draw food and cookware through snapshots. Sort the chef/held plate with feet
   and tables with floor bases. Bodies may overlap raised surfaces naturally;
   feet must never enter a wall, counter, crate, cooker or bin.
6. Let the order system draw the sidebar in the existing screen UI camera.
   Remove placeholder text once the real sidebar is connected. Text and icons
   must stay readable after resizing at 100%, 125%, 150% and 200% Windows scale.
7. Coordinate audio pause/resume and reset with Member 2's sound component.
   A rejected action must not play the success sound or alter the score.

## Public interfaces to preserve

PlayerController: set_move_key, update, clear_input, reset, position,
ground_position, direction, state, sprite. choose_target returns one target or
None. GameView is the coordinator, not the food/order data store.

Station IDs: box_sandwich, box_tomato, box_noodles, box_milk, plate, bin,
serve and chopping_board. Add a stable pot target kind/ID with Member 2. All
maps must have reachable counterparts. Do not silently rename IDs per room.

## Acceptance checks

- Walk every aisle in each of four rooms, approach each station and slide along
  each counter. No invisible halo and no walking through floor furniture.
- Hold two movement keys, release one, pause/resume, change map and unfocus the
  window. The chef must not keep moving from a stale key.
- Finish the complete flow described in Member 2's guide: collect, plate/cook,
  carry, serve, retain empty plate, return plate, start another order.
- Correct order completes once; wrong order preserves food and plate. Repeating
  a key or serving twice cannot score twice. Empty or occupied hands have clear
  feedback. Reset and map switching restore a predictable clean state.
- Resize the window tall/wide and maximize it. The full room and sidebar remain
  visible and readable. No important controls are outside the screen.

## Deliver and verify

Run python -m pytest tests -q and python main.py --self-test artifacts/check on a
Windows desktop. Add meaningful end-to-end checks for new behavior; preserve
existing regression checks. Build with PyInstaller using PlayerDemo.spec and
include all four maps, food PNGs and audio. Extract the ZIP into a fresh folder
with spaces and play it without Python installed. Keep _internal beside the EXE.

Provide a playable ZIP, screenshots of all four maps, controls, test results and
an honest unfinished-items list. Do not call the milestone complete until all
four maps support the same food-to-service loop.
