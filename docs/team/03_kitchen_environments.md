# Member 3 — Two kitchens and two damaged variants

Read [TEAM_PLAN.md](../TEAM_PLAN.md). You own environment art and measured map
layouts. Member 1 integrates map switching/cameras; Member 2 owns food behavior.
Use [our warm kitchen screenshot](../images/kitchen_preview.png) as the finished
composition reference. Match its complete-room presentation in the second room.

## Four required environments

| Map ID | Required appearance |
| --- | --- |
| warm_clean | Existing warm wood/teal kitchen, complete and tidy |
| warm_overgrown | SAME kitchen, rotting wood, damp marks, vines/plants, cracked tiles |
| metal_clean | Second kitchen: silver/stainless steel, metallic counters and appliances |
| metal_damaged | SAME metallic kitchen with dents, rust, broken panels and wear |

Provide all four, including the existing warm room's finished assets/layout.
The damaged warm kitchen must look overgrown/rotting, not simply tinted green.
The damaged metal room must show physical metal damage, not merely dark lighting.
The clean and damaged versions must remain recognizable as the same room.

## Design requirements

Use the same low top-down view as the separate furniture at the bottom of the
original supplied kitchen sheet. Keep straight front edges and one consistent
viewpoint. Do not paste a perspective room image across the upper part of a flat
floor. Show the entire kitchen with a readable chef-to-counter size relationship.
Reference: chef 56 x 92; current tables 180 x 110; room 960 x 704. Keep this room
size for the milestone so the sidebar/window setup stays consistent.

Each room needs pantry crates, sink/draining area, cooker with a pot correctly
aligned to one burner, a distinct chopping-board island, a clear plate island,
bin and a service hatch visibly opening into a dining room. Include coherent
wall details such as shelves, utensils, hood, towels, lamps and order tickets.
Place them where a kitchen would use them; avoid loose food scattered on tables.
The plate island starts with only its empty plate; food is rendered dynamically.

Reuse Member 2's food and pot sprites. Do not bake food, a plate or a pot into a
new background where it must later disappear or change. Render changeable
objects as separate transparent sprites. Decorative shelves may contain jars,
but pantry pickups/plate contents remain owned by the food system.

## Damage without breaking gameplay

For each clean/damaged pair keep room dimensions, spawn, station IDs, approach
points and furniture footprints identical for this milestone. Damage is visual;
all kitchens must still support the same recipe-to-service loop. Put vines on
walls/trim and rotten details on existing furniture. Do not hide the chopping
board, plate, pot, serving hatch or interaction prompts behind vegetation.

If you add a floor-standing plant or debris object, give it an accurate footprint
and send the layout change to Member 1 for route checks. Prefer wall growth and
flat cracks/stains so a visual variant does not silently obstruct a station.
Keep safe routes from pantry to prep/cooker to plate to service and back.

## Files and map handoff

Put assets under assets/kitchen/warm_clean/, warm_overgrown/, metal_clean/ and
metal_damaged/. Use consistent object filenames across variants. Provide a small
manifest of file names, sizes and transparent-sprite crop regions if using an
atlas. PNG with clean alpha for props; avoid white rectangles, JPEG fringes or
untrimmed neighboring objects. Keep original working art outside runtime assets
or in a clearly named source-art directory.

Coordinate environment data with Member 1 in restaurant/kitchen/. Each definition
needs map_id, world size, spawn, prop artwork rectangles, local floor footprints,
wall art and target points. Existing KitchenProp distinguishes the visible
rectangle from collision_rectangle. Measure bases; do not expand collision to
cover transparent padding, the full chef height or wall decoration.

Required target IDs: box_sandwich, box_tomato, box_noodles, box_milk, plate, bin,
serve, chopping_board and the pot ID agreed with Member 2. All four maps use the
same ID meanings. Floor interaction points use the chef's sprite center; its
foot center is 32 pixels below it. F1 reveals real solid outlines and ranges.

## Optional art prompts

Use these only if image generation helps; otherwise draw/edit the art yourself.
Reference both the supplied metallic sheet and our warm screenshot. Generate
separate backgrounds/transparent sprites so gameplay items stay removable.

Metal clean prompt:
"Create a complete restaurant kitchen game environment matching the reference's
low top-down orthographic view, consistent pixel-art scale and crisp outlines.
Use brushed silver stainless steel counters, a steel sink/drainer, a cooker
and hood, a separate chopping island, an empty plate island and a service hatch
with a dining room visible beyond. Include practical shelves/utensils/lighting.
Maintain the reference layout and walkable aisles at a 960 x 704 world size.
No chef, food, plate, pot, text, UI or baked-in interaction markers. Supply floor
and wall art separately from transparent furniture sprites. No perspective
photo strip, isometric angle, glossy 3D rendering or blur."

Warm overgrown prompt:
"Edit the warm clean kitchen assets as their overgrown counterpart. Preserve
camera, exact object placement, dimensions, silhouettes, empty work areas and
station access. Show rotting wood, damp discoloration, small wall vines and
plants, chipped teal paint and cracked tiles. Keep the kitchen recognizable and
workstations legible. Preserve transparent backgrounds. No new floor obstacles,
chef, food, plate, pot, text or UI."

Metal damaged prompt:
"Edit the silver clean kitchen assets as their damaged counterpart. Preserve
camera, exact layout, dimensions, station access and furniture silhouettes.
Add dents, rust around joints, scratched steel, bent cabinet panels and worn
tiles. Keep sink, stove, chopping board and service hatch recognizable and
reachable. Preserve transparency. No new floor obstacles, chef, food, plate,
pot, text or UI."

If the tool ignores dimensions/grid alignment, correct the asset placement and
verify the map in-game rather than trusting the generated picture as a collider.
Record the tool/prompt used and asset sources/licenses in your handoff.

## Completion checklist

- Four environment definitions and complete required art, not mockup-only images.
- Each clean/damaged pair aligned identically; no hidden baked-in gameplay food.
- Empty and food-loaded scene screenshots of each room at the actual game size.
- Chef can reach every station, touch counter edges naturally, walk behind/in
  front correctly, and never leave walls or enter furniture bases.
- Pot/board/plate fit their surfaces and transparent edges look clean.
- The second kitchen feels like a complete restaurant, including outgoing service.
- Member 1 can select all maps without copying whole scenes. Commit only your
  assets/layout data and agreed renderer changes; describe anything incomplete.
